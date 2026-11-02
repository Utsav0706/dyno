"""How far each judge agrees with a human (`dyno calibrate`).

Cohen's kappa, not plain agreement: if 95% of answers pass, a judge that always says
"pass" agrees 95% of the time and knows nothing. Kappa = (observed - chance) /
(1 - chance), where chance is the agreement expected from each side's pass rate alone.
1 is perfect, 0 is chance; Dyno's bar for trusting a judge is 0.6 (the usual
"substantial agreement" threshold).

The judge side is the score stored now, so after a prompt change and a re-score, the
same labels measure the new judge.
"""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel

from dyno.store.models import Label

KAPPA_BAR = 0.6


class Pair(BaseModel):
    run_id: str
    case_id: str
    attempt: int
    item: str
    human: bool
    judge: bool
    reason: str  # the judge's explanation
    note: str  # the labeller's note


class ScorerCalibration(BaseModel):
    scorer: str
    n: int
    agreement: float | None
    kappa: float | None  # None when it can't be computed (one side always the same)
    # Human verdict x judge verdict: [[both pass, human pass / judge fail],
    #                                 [human fail / judge pass, both fail]]
    matrix: list[list[int]]
    unsure: int  # labels marked unsure, left out
    stale: int  # labels whose judged item no longer exists (e.g. re-scored claims)
    judges: list[str]  # model and prompt versions behind the judge side
    disagreements: list[Pair]

    @property
    def trusted(self) -> bool:
        return self.kappa is not None and self.kappa >= KAPPA_BAR


def cohen_kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    n = len(pairs)
    if not n:
        return None
    observed = sum(h == j for h, j in pairs) / n
    h_yes = sum(h for h, _ in pairs) / n
    j_yes = sum(j for _, j in pairs) / n
    chance = h_yes * j_yes + (1 - h_yes) * (1 - j_yes)
    if chance == 1:
        return None  # both sides gave one verdict throughout: nothing to measure
    return (observed - chance) / (1 - chance)


def _judge_side(label: Label) -> tuple[bool | None, str, str | None]:
    """(judge verdict, its reason, model/prompt) for what this label checks."""
    score = next((s for s in label.result.scores if s.scorer == label.scorer), None)
    if score is None:
        return None, "", None
    meta = score.details.get("judge") or {}
    version = f"{meta.get('model')} / {meta.get('prompt')}" if meta else None
    if not label.item:
        return score.passed, score.explanation, version
    for c in score.details.get("claims", []):
        if c["claim"] == label.item and not c.get("meta"):
            return c["supported"], f"judge cited: {c.get('evidence') or 'nothing'}", version
    return None, "", version


def calibrate(labels: list[Label]) -> list[ScorerCalibration]:
    grouped: dict[str, list[Label]] = defaultdict(list)
    for lab in labels:
        grouped[lab.scorer].append(lab)
    out = []
    for scorer in sorted(grouped):
        pairs: list[Pair] = []
        unsure = stale = 0
        versions: set[str] = set()
        for lab in grouped[scorer]:
            if lab.label is None:
                unsure += 1
                continue
            judge, reason, version = _judge_side(lab)
            if judge is None:
                stale += 1
                continue
            if version:
                versions.add(version)
            r = lab.result
            pairs.append(
                Pair(
                    run_id=r.run_id,
                    case_id=r.case_id,
                    attempt=r.attempt,
                    item=lab.item,
                    human=lab.label,
                    judge=judge,
                    reason=reason,
                    note=lab.note,
                )
            )
        verdicts = [(p.human, p.judge) for p in pairs]
        matrix = [
            [sum(1 for h, j in verdicts if h and j), sum(1 for h, j in verdicts if h and not j)],
            [
                sum(1 for h, j in verdicts if not h and j),
                sum(1 for h, j in verdicts if not h and not j),
            ],
        ]
        out.append(
            ScorerCalibration(
                scorer=scorer,
                n=len(pairs),
                agreement=sum(h == j for h, j in verdicts) / len(pairs) if pairs else None,
                kappa=cohen_kappa(verdicts),
                matrix=matrix,
                unsure=unsure,
                stale=stale,
                judges=sorted(versions),
                disagreements=[p for p in pairs if p.human != p.judge],
            )
        )
    return out


def _cell(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())[:300]


def to_markdown(results: list[ScorerCalibration]) -> str:
    lines = [
        "# Judge calibration",
        "",
        f"Cohen's kappa between the judge and hand labels. Bar: {KAPPA_BAR}. The sample "
        "takes every item the judge failed plus a random share of the rest, so both "
        "verdicts are well represented (this raises the share of fails above the real "
        "rate). Labels marked unsure are left out.",
        "",
        "| Judge | Labels | Agreement | Kappa | Verdict | Judged by |",
        "|---|---|---|---|---|---|",
    ]
    for c in results:
        kappa = "n/a" if c.kappa is None else f"{c.kappa:.2f}"
        agree = "n/a" if c.agreement is None else f"{c.agreement:.0%}"
        verdict = "trusted" if c.trusted else "**below the bar**"
        lines.append(
            f"| {c.scorer} | {c.n} | {agree} | {kappa} | {verdict} | {'; '.join(c.judges)} |"
        )
    for c in results:
        (pp, pf), (fp, ff) = c.matrix
        lines += [
            "",
            f"## {c.scorer}",
            "",
            "| | judge pass | judge fail |",
            "|---|---|---|",
            f"| **human pass** | {pp} | {pf} |",
            f"| **human fail** | {fp} | {ff} |",
            "",
            f"Unsure (left out): {c.unsure}. No longer judged (left out): {c.stale}.",
        ]
        if c.disagreements:
            lines += [
                "",
                "| Case | # | Item | Human | Judge | Judge's reason | Note |",
                "|---|---|---|---|---|---|---|",
            ]
            for d in c.disagreements:
                lines.append(
                    f"| `{d.case_id}` | {d.attempt} | {_cell(d.item)} | "
                    f"{'pass' if d.human else 'fail'} | {'pass' if d.judge else 'fail'} | "
                    f"{_cell(d.reason)} | {_cell(d.note)} |"
                )
    return "\n".join(lines) + "\n"
