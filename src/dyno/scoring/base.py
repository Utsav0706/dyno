"""Scorer plumbing: what a scorer gets, what it returns, and the registry.

Scorers take an `Attempt` (answer + steps + timing), which is built either from a live
AgentResult or from stored rows. So a stored run can be re-scored for free
(`dyno score RUN_ID`) without calling the agent again.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel

from dyno.agent import AgentResult, Step
from dyno.cases import Case, ScorerSpec

log = logging.getLogger(__name__)


class Score(BaseModel):
    # 0..1, higher is better; None when the scorer has no number to give.
    score: float | None = None
    # None = this scorer doesn't apply to this case (e.g. no max_steps, no expected).
    # Not applicable never counts as a pass or a fail.
    passed: bool | None = None
    explanation: str = ""
    details: dict[str, Any] = {}


class Attempt(BaseModel):
    final_answer: str = ""
    steps: list[Step] = []
    error: str | None = None
    latency_ms: float = 0.0

    @classmethod
    def from_result(cls, result: AgentResult, latency_ms: float) -> Attempt:
        return cls(
            final_answer=result.final_answer,
            steps=result.steps,
            error=result.error,
            latency_ms=latency_ms,
        )

    def total(self, field: str) -> float | None:
        """Sum of a step field (tokens, cost); None if no step reported it."""
        values = [getattr(s, field) for s in self.steps if getattr(s, field) is not None]
        return sum(values) if values else None

    @property
    def tool_calls(self) -> list[Step]:
        return [s for s in self.steps if s.type == "tool_call"]


class Scorer(Protocol):
    name: ClassVar[str]
    # A crashed attempt fails this scorer outright. cost_latency sets False: the time
    # and money a failed attempt used are still real.
    fails_on_error: ClassVar[bool]

    def score(self, case: Case, attempt: Attempt) -> Score: ...


_REGISTRY: dict[str, Callable[..., Scorer]] = {}
# Used when a suite lists no scorers. Judge scorers (M4) cost money, so they're opt-in.
DETERMINISTIC = ["task_success", "tool_correctness", "trajectory_efficiency", "cost_latency"]


def register[T](name: str) -> Callable[[type[T]], type[T]]:
    def deco(cls: type[T]) -> type[T]:
        cls.name = name  # type: ignore[attr-defined]
        _REGISTRY[name] = cls  # type: ignore[assignment]
        return cls

    return deco


def parse_spec(spec: ScorerSpec) -> tuple[str, dict[str, Any]]:
    if isinstance(spec, str):
        return spec, {}
    if len(spec) != 1:
        raise ValueError(f"scorer entry must have exactly one name: {spec}")
    ((name, params),) = spec.items()
    return name, params or {}


def build_scorers(specs: list[ScorerSpec]) -> list[Scorer]:
    """Scorers for a suite. Fails before the run starts on unknown names or bad params."""
    from dyno import scoring  # noqa: F401  (importing registers the built-in scorers)

    scorers = []
    for spec in specs or DETERMINISTIC:
        name, params = parse_spec(spec)
        if name not in _REGISTRY:
            raise ValueError(f"unknown scorer {name!r}: known are {', '.join(sorted(_REGISTRY))}")
        try:
            scorers.append(_REGISTRY[name](**params))
        except TypeError as exc:
            raise ValueError(f"scorer {name}: bad settings {params}: {exc}") from exc
    return scorers


def score_attempt(scorers: list[Scorer], case: Case, attempt: Attempt) -> dict[str, Score]:
    scores: dict[str, Score] = {}
    for scorer in scorers:
        if attempt.error and scorer.fails_on_error:
            scores[scorer.name] = Score(
                score=0.0, passed=False, explanation=f"agent error: {attempt.error}"
            )
            continue
        try:
            scores[scorer.name] = scorer.score(case, attempt)
        except Exception as exc:  # judge API down or over budget, bad regex, broken check
            # Not applicable, not failed: a scorer's own failure says nothing about the
            # agent. The report counts these separately, so they can't hide either.
            log.warning(
                "scorer failed",
                extra={"scorer": scorer.name, "case_id": case.id, "error": str(exc)[:200]},
            )
            scores[scorer.name] = Score(
                explanation=f"scorer error: {type(exc).__name__}: {exc}",
                details={"scorer_error": True},
            )
    return scores


def attempt_passed(passed: list[bool | None]) -> bool | None:
    """An attempt passes when every scorer that applied passed; None if none applied."""
    applied = [p for p in passed if p is not None]
    return all(applied) if applied else None
