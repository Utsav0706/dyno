"""cost_latency: what an attempt cost and how long it took.

For information only unless the suite sets limits (max_cost_gbp, max_latency_s); then
it passes or fails on them. An unknown cost (the agent didn't report one) skips the
cost limit rather than failing it.
"""

from __future__ import annotations

from typing import ClassVar

from dyno.cases import Case
from dyno.scoring.base import Attempt, Score, register


@register("cost_latency")
class CostLatency:
    name: ClassVar[str]
    fails_on_error: ClassVar[bool] = False

    def __init__(
        self, max_cost_gbp: float | None = None, max_latency_s: float | None = None
    ) -> None:
        self.max_cost_gbp = max_cost_gbp
        self.max_latency_s = max_latency_s

    def score(self, case: Case, attempt: Attempt) -> Score:
        cost = attempt.total("cost_gbp")
        seconds = attempt.latency_ms / 1000
        details = {
            "cost_gbp": cost,
            "latency_s": seconds,
            "input_tokens": attempt.total("input_tokens"),
            "output_tokens": attempt.total("output_tokens"),
        }
        cost_text = "cost unknown" if cost is None else f"GBP {cost:.4f}"
        summary = f"{cost_text}, {seconds:.1f}s"

        checks: list[bool] = []
        over: list[str] = []
        if self.max_cost_gbp is not None and cost is not None:
            checks.append(cost <= self.max_cost_gbp)
            if not checks[-1]:
                over.append(f"cost > GBP {self.max_cost_gbp}")
        if self.max_latency_s is not None:
            checks.append(seconds <= self.max_latency_s)
            if not checks[-1]:
                over.append(f"time > {self.max_latency_s}s")
        if not checks:
            return Score(explanation=summary, details=details)
        ok = all(checks)
        return Score(
            score=float(ok),
            passed=ok,
            explanation=summary + ("" if ok else f" ({'; '.join(over)})"),
            details=details,
        )
