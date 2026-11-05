"""Pass/fail a candidate run against a baseline (`dyno gate`), for CI and Pitwall.

    from dyno.gate import gate
    result = gate("cand_run_id", "base_run_id", max_drop=2.0)
    if not result.passed: ...

The metric is a pass rate (the attempt pass rate by default, or pass@k / pass^k, or one
scorer's pass rate), compared on the cases both runs share. The gate fails when it
drops by more than `max_drop` percentage points, and optionally when any case that
passed before now fails.

Noise: on 50 cases, 2 points is one case, and agents are random. Gate on runs with
k = 3 (pass^k or the attempt pass rate over 150 attempts) so one unlucky attempt
doesn't decide a release.
"""

from __future__ import annotations

from pydantic import BaseModel

from dyno.compare import HEADLINE, compare_ids
from dyno.config import get_settings
from dyno.store import Store, open_engine


class GateResult(BaseModel):
    passed: bool
    metric: str
    baseline: float | None
    candidate: float | None
    drop_pp: float | None  # positive = worse
    max_drop: float
    compared_cases: int
    newly_failing: list[str]
    reason: str


def gate(
    candidate: str,
    baseline: str,
    *,
    max_drop: float = 2.0,
    metric: str = "attempt_pass_rate",
    no_new_failures: bool = False,
    store: Store | None = None,
) -> GateResult:
    store = store or Store(open_engine(get_settings().database_url))
    # Gating on one scorer: newly failing cases are judged by that scorer alone too.
    scorer = None if metric in HEADLINE else metric
    c = compare_ids(store, baseline, candidate, scorer)

    def result(
        passed: bool,
        reason: str,
        base: float | None = None,
        cand: float | None = None,
        drop: float | None = None,
    ) -> GateResult:
        return GateResult(
            passed=passed,
            metric=metric,
            baseline=base,
            candidate=cand,
            drop_pp=drop,
            max_drop=max_drop,
            compared_cases=c.common_cases,
            newly_failing=c.newly_failing,
            reason=reason,
        )

    if not c.common_cases:
        return result(False, "the runs share no cases, so there is nothing to compare")
    m = c.metric(metric)
    if m is None:
        known = ", ".join(x.metric for x in c.metrics)
        return result(False, f"unknown metric {metric!r}; known: {known}")
    if m.a is None or m.b is None:
        return result(False, f"{metric} has no value in one of the runs", m.a, m.b)
    drop = (m.a - m.b) * 100
    if drop > max_drop:
        why = f"{metric} dropped {drop:.1f} pts ({m.a:.0%} -> {m.b:.0%}), more than {max_drop}"
        return result(False, why, m.a, m.b, drop)
    if no_new_failures and c.newly_failing:
        why = f"{len(c.newly_failing)} case(s) that passed now fail: {', '.join(c.newly_failing)}"
        return result(False, why, m.a, m.b, drop)
    return result(
        True, f"{metric} {m.a:.0%} -> {m.b:.0%} (allowed drop {max_drop} pts)", m.a, m.b, drop
    )
