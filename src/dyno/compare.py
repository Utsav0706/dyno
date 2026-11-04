"""What changed between two runs (`dyno compare`), on the cases both ran.

Runs with different cases (a different config hash) can still be compared, but only on
the shared cases, and the comparison says how many were left out: a pass rate over
other questions isn't a like-for-like number.

A case "passes" when every judged attempt passed (pass^k), "fails" when none did, and
is "flaky" in between.
"""

from __future__ import annotations

from pydantic import BaseModel

from dyno.report import Report, build_report
from dyno.scoring.reliability import CaseReliability
from dyno.store import Store
from dyno.store.models import Run

# Headline metrics, then one per scorer.
HEADLINE = ("attempt_pass_rate", "pass_at_k", "pass_hat_k")


class MetricDelta(BaseModel):
    metric: str
    a: float | None
    b: float | None

    @property
    def delta_pp(self) -> float | None:
        """Change in percentage points (b - a)."""
        return None if self.a is None or self.b is None else (self.b - self.a) * 100


class Comparison(BaseModel):
    run_a: str
    run_b: str
    same_config: bool
    common_cases: int
    only_a: list[str]
    only_b: list[str]
    metrics: list[MetricDelta]
    cost_per_attempt_a: float | None
    cost_per_attempt_b: float | None
    latency_p50_a: float | None
    latency_p50_b: float | None
    newly_failing: list[str]  # passed in A, failed in B
    newly_flaky: list[str]  # passed in A, flaky in B
    newly_passing: list[str]  # didn't pass in A, passes in B

    def metric(self, name: str) -> MetricDelta | None:
        return next((m for m in self.metrics if m.metric == name), None)


def case_status(cr: CaseReliability) -> str:
    if not cr.attempts:
        return "n/a"
    if cr.pass_hat_k:
        return "pass"
    return "flaky" if cr.pass_at_k else "fail"


def _metrics(rep: Report) -> dict[str, float | None]:
    out: dict[str, float | None] = {m: getattr(rep, m) for m in HEADLINE}
    out.update({s.scorer: s.pass_rate for s in rep.scorers})
    return out


def compare_runs(a: Run, b: Run) -> Comparison:
    ids_a = {c.case_id for c in a.cases}
    ids_b = {c.case_id for c in b.cases}
    common = ids_a & ids_b
    rep_a, rep_b = build_report(a, common), build_report(b, common)
    ma, mb = _metrics(rep_a), _metrics(rep_b)
    names = list(HEADLINE) + sorted((set(ma) | set(mb)) - set(HEADLINE))

    status_a = {cr.case_id: case_status(cr) for cr in rep_a.reliability}
    status_b = {cr.case_id: case_status(cr) for cr in rep_b.reliability}
    order = sorted(common)
    return Comparison(
        run_a=a.id,
        run_b=b.id,
        same_config=a.config_hash == b.config_hash,
        common_cases=len(common),
        only_a=sorted(ids_a - common),
        only_b=sorted(ids_b - common),
        metrics=[MetricDelta(metric=n, a=ma.get(n), b=mb.get(n)) for n in names],
        cost_per_attempt_a=rep_a.cost_per_attempt_gbp,
        cost_per_attempt_b=rep_b.cost_per_attempt_gbp,
        latency_p50_a=rep_a.latency_p50_s,
        latency_p50_b=rep_b.latency_p50_s,
        newly_failing=[c for c in order if status_a[c] == "pass" and status_b[c] == "fail"],
        newly_flaky=[c for c in order if status_a[c] == "pass" and status_b[c] == "flaky"],
        newly_passing=[
            c for c in order if status_a[c] in ("fail", "flaky") and status_b[c] == "pass"
        ],
    )


def compare_ids(store: Store, run_a: str, run_b: str) -> Comparison:
    runs = [store.get_run(run_a), store.get_run(run_b)]
    missing = [i for i, r in zip((run_a, run_b), runs, strict=True) if r is None]
    if missing:
        raise LookupError(f"no run {', '.join(missing)}")
    return compare_runs(runs[0], runs[1])  # type: ignore[arg-type]


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def to_markdown(c: Comparison) -> str:
    lines = [
        f"# Dyno compare: `{c.run_a}` -> `{c.run_b}`",
        "",
        f"Compared on {c.common_cases} shared cases"
        + ("" if c.same_config else " (**different configs**: cases, scorers, agent or k differ)")
        + (f"; only in A: {len(c.only_a)}" if c.only_a else "")
        + (f"; only in B: {len(c.only_b)}" if c.only_b else "")
        + ".",
        "",
        "| Metric | A | B | Change |",
        "|---|---|---|---|",
    ]
    for m in c.metrics:
        d = m.delta_pp
        change = "n/a" if d is None else f"{d:+.1f} pts"
        lines.append(f"| {m.metric} | {_pct(m.a)} | {_pct(m.b)} | {change} |")

    def gbp(x: float | None) -> str:
        return "n/a" if x is None else f"GBP {x:.4f}"

    def secs(x: float | None) -> str:
        return "n/a" if x is None else f"{x:.1f}s"

    lines += [
        f"| cost per attempt | {gbp(c.cost_per_attempt_a)} | {gbp(c.cost_per_attempt_b)} | |",
        f"| latency p50 | {secs(c.latency_p50_a)} | {secs(c.latency_p50_b)} | |",
    ]
    for title, ids in (
        ("Newly failing", c.newly_failing),
        ("Newly flaky", c.newly_flaky),
        ("Newly passing", c.newly_passing),
    ):
        lines += ["", f"## {title} ({len(ids)})", ""]
        lines += [f"- `{i}`" for i in ids] or ["None."]
    return "\n".join(lines) + "\n"
