"""Judge scorers: an LLM grades what code can't (key points in other words, claims vs
evidence, overall quality). Each makes one structured call per attempt.

The pass rules live here, in code, not in the prompts: the same rule applies to every
case, and changing it doesn't mean re-wording (and re-validating) a prompt.
These cost money, so a suite has to list them; they're not in the default set.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from dyno.cases import Case
from dyno.judge import get_judge, load_prompt
from dyno.scoring.base import Attempt, Score, register

# --- task_rubric ---


class KeyPointGrade(BaseModel):
    point: int
    covered: bool


class TaskGrade(BaseModel):
    key_points: list[KeyPointGrade]
    contradicts_key: bool
    states_insufficient_evidence: bool
    gives_specific_answer: bool
    reason: str


@register("task_rubric")
class TaskRubric:
    """Did the answer cover every expected key point, without contradicting any?
    For an unanswerable case (no `expected`, tagged `unanswerable`): did it say the
    evidence isn't there, without inventing an answer?"""

    name: ClassVar[str]
    fails_on_error: ClassVar[bool] = True
    uses_judge: ClassVar[bool] = True  # costs money; checked before a run starts

    def __init__(self, prompt: str = "judge_task_v1", unanswerable_tag: str = "unanswerable"):
        self.prompt = load_prompt(prompt)
        self.unanswerable_tag = unanswerable_tag

    def score(self, case: Case, attempt: Attempt) -> Score:
        points = [case.expected] if isinstance(case.expected, str) else (case.expected or [])
        unanswerable = not points and self.unanswerable_tag in case.tags
        if not points and not unanswerable:
            return Score(explanation="no expected answer")
        if not attempt.final_answer.strip():
            return Score(score=0.0, passed=False, explanation="empty answer")

        if unanswerable:
            key = "UNANSWERABLE: the evidence needed does not exist or is not available."
        else:
            key = "\n".join(f"{i}. {p}" for i, p in enumerate(points, start=1))
        verdict = get_judge().ask(
            self.prompt,
            f"<question>\n{case.input}\n</question>\n\n<answer_key>\n{key}\n</answer_key>\n\n"
            f"<answer>\n{attempt.final_answer}\n</answer>",
            TaskGrade,
        )
        g = verdict.parsed
        details = {"grade": g.model_dump(), "judge": verdict.meta(self.prompt)}
        if unanswerable:
            ok = g.states_insufficient_evidence and not g.gives_specific_answer
            return Score(score=float(ok), passed=ok, explanation=g.reason, details=details)
        covered = {kp.point for kp in g.key_points if kp.covered} & set(range(1, len(points) + 1))
        share = len(covered) / len(points)
        ok = share == 1.0 and not g.contradicts_key
        return Score(score=share, passed=ok, explanation=g.reason, details=details)


# --- hallucination ---


class ClaimCheck(BaseModel):
    claim: str
    # About the answer or the search ("the sources don't state X"), not about the world.
    # Not checked: such a statement can't be supported by a passage, and counting it
    # would mark down an agent for honestly saying what it couldn't find.
    meta: bool
    supported: bool
    evidence: str


class ClaimChecks(BaseModel):
    claims: list[ClaimCheck]


@register("hallucination")
class Hallucination:
    """Share of the answer's factual claims that the agent's own evidence doesn't
    support. Evidence = the case's `sources` plus the tool results the agent received
    (from its trajectory), so it checks what the agent saw, not what the judge knows.
    Score = 1 - unsupported rate; passes when the rate <= max_unsupported_rate."""

    name: ClassVar[str]
    fails_on_error: ClassVar[bool] = True
    uses_judge: ClassVar[bool] = True  # costs money; checked before a run starts

    def __init__(
        self,
        prompt: str = "judge_hallucination_v2",
        max_unsupported_rate: float = 0.1,
        exclude_tools: list[str] | None = None,
        max_evidence_chars: int = 300_000,
    ) -> None:
        self.prompt = load_prompt(prompt)
        self.max_rate = max_unsupported_rate
        # Tools whose output is the agent's own writing (e.g. Scout's save_note), not
        # evidence it was given.
        self.exclude_tools = set(exclude_tools or [])
        # ~75K tokens: bounds the cost of one call (about GBP 0.006 on Haiku) and stays
        # under Haiku 5.5's 100K-token price step. Passages past it are dropped and
        # counted, so a claim they'd support can show up as unsupported.
        self.max_chars = max_evidence_chars

    def evidence(self, case: Case, attempt: Attempt) -> tuple[list[str], int]:
        """Labelled passages within the character cap, and how many were left out."""
        texts = list(case.sources)
        texts += [
            f"({s.name}) {s.output}"
            for s in attempt.steps
            if s.type == "tool_result"
            and s.output
            and s.name not in self.exclude_tools
            and s.args.get("ok", True)
        ]
        # The same search result or page often comes back more than once: send it once.
        texts = list(dict.fromkeys(texts))
        kept, used = [], 0
        for i, text in enumerate(texts, start=1):
            if used + len(text) > self.max_chars:
                return kept, len(texts) - len(kept)
            kept.append(f"[E{i}] {text}")
            used += len(text)
        return kept, 0

    def score(self, case: Case, attempt: Attempt) -> Score:
        if not attempt.final_answer.strip():
            return Score(explanation="empty answer")
        passages, dropped = self.evidence(case, attempt)
        if not passages:
            return Score(explanation="no evidence to check claims against")

        verdict = get_judge().ask(
            self.prompt,
            f"<answer>\n{attempt.final_answer}\n</answer>\n\n<evidence>\n"
            + "\n\n".join(passages)
            + "\n</evidence>",
            ClaimChecks,
        )
        everything = verdict.parsed.claims
        claims = [c for c in everything if not c.meta]
        details = {
            "claims": [c.model_dump() for c in everything],
            "meta_statements": len(everything) - len(claims),
            "evidence_passages": len(passages),
            "evidence_dropped": dropped,
            "judge": verdict.meta(self.prompt),
        }
        if not claims:
            return Score(score=1.0, passed=True, explanation="no factual claims", details=details)
        unsupported = [c.claim for c in claims if not c.supported]
        rate = len(unsupported) / len(claims)
        details["unsupported_rate"] = rate
        explanation = f"{len(unsupported)}/{len(claims)} claims unsupported"
        if unsupported:
            explanation += ": " + "; ".join(u[:80] for u in unsupported[:3])
        return Score(
            score=1 - rate, passed=rate <= self.max_rate, explanation=explanation, details=details
        )


# --- quality ---


class QualityGrade(BaseModel):
    correct: int
    helpful: int
    clear: int
    reason: str


@register("quality")
class Quality:
    """1-5 for correct, helpful and clear; passes when their mean >= min_score."""

    name: ClassVar[str]
    fails_on_error: ClassVar[bool] = True
    uses_judge: ClassVar[bool] = True  # costs money; checked before a run starts

    def __init__(self, prompt: str = "judge_quality_v1", min_score: float = 4.0) -> None:
        self.prompt = load_prompt(prompt)
        self.min_score = min_score

    def score(self, case: Case, attempt: Attempt) -> Score:
        if not attempt.final_answer.strip():
            return Score(score=0.0, passed=False, explanation="empty answer")
        if isinstance(case.expected, str):
            reference = case.expected
        elif case.expected:
            reference = "\n".join(f"- {p}" for p in case.expected)
        elif "unanswerable" in case.tags:
            reference = "This question cannot be answered from available evidence."
        else:
            reference = "(none)"
        verdict = get_judge().ask(
            self.prompt,
            f"<question>\n{case.input}\n</question>\n\n<reference>\n{reference}\n</reference>"
            f"\n\n<answer>\n{attempt.final_answer}\n</answer>",
            QualityGrade,
        )
        g = verdict.parsed
        # Clamp: the schema says int, not 1-5, and a stray 0 or 6 shouldn't skew means.
        parts = [min(5, max(1, v)) for v in (g.correct, g.helpful, g.clear)]
        mean = sum(parts) / 3
        return Score(
            score=(mean - 1) / 4,
            passed=mean >= self.min_score,
            explanation=f"{mean:.1f}/5 (correct {parts[0]}, helpful {parts[1]}, "
            f"clear {parts[2]}): {g.reason}",
            details={"grade": g.model_dump(), "mean": mean, "judge": verdict.meta(self.prompt)},
        )
