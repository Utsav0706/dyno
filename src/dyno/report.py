"""Build a run's report once as a Pydantic model, then render it as Markdown or JSON.

One model, two renderers: the Markdown a person reads and the JSON that `compare`,
`gate` and the dashboard read can't disagree.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime

from pydantic import BaseModel

from dyno.scoring.base import attempt_passed
from dyno.scoring.reliability import CaseReliability, case_reliability
from dyno.store.models import Run

AGENT_ERROR = "(agent error)"


class ScorerStats(BaseModel):
    scorer: str
    scored: int  # attempts where the scorer applied
    passed: int
    skipped: int  # not applicable
    errors: int  # the scorer itself failed (e.g. judge API down); not counted as a fail
    pass_rate: float | None
    mean_score: float | None


class TagStats(BaseModel):
    tag: str
    cases: int
    attempts: int
    passed: int
    pass_rate: float | None


class Failure(BaseModel):
    case_id: str
    scorer: str
    failed: int  # attempts that failed this scorer
    attempts: int
    explanation: str  # from the first failing attempt


class Report(BaseModel):
    run_id: str
    suite: str
    agent: str
    k: int
    status: str
    git_commit: str | None
    git_dirty: bool | None
    config_hash: str
    dyno_version: str
    started_at: datetime
    finished_at: datetime | None

    cases: int
    attempts: int
    errors: int
    attempts_passed: int
    attempt_pass_rate: float | None
    pass_at_k: float | None  # share of cases with at least one passing attempt
    pass_hat_k: float | None  # share of cases where every attempt passed
    flaky: list[str]

    cost_gbp: float | None
    judge_cost_gbp: float  # judge spend behind the scores now stored (latest re-score only)
    cost_per_attempt_gbp: float | None
    input_tokens: int
    output_tokens: int
    latency_p50_s: float | None
    latency_p95_s: float | None

    scorers: list[ScorerStats]
    tags: list[TagStats]
    reliability: list[CaseReliability]
    failures: list[Failure]


def _rate(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def _percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile: always an observed value, fine for small runs."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def build_report(run: Run, only: set[str] | None = None) -> Report:
    """`only`: restrict to these case ids (compare/gate use the cases two runs share)."""
    results = [r for r in run.results if only is None or r.case_id in only]
    run_cases = [c for c in run.cases if only is None or c.case_id in only]
    outcome = {
        r.id: attempt_passed([sc.passed for sc in r.scores]) for r in results
    }  # result id -> passed / failed / None

    by_case: dict[str, list[bool | None]] = defaultdict(list)
    for r in results:
        by_case[r.case_id].append(outcome[r.id])
    reliability = [case_reliability(c.case_id, by_case[c.case_id]) for c in run_cases]
    judged = [cr for cr in reliability if cr.attempts]

    stats: dict[str, list[tuple[bool | None, float | None]]] = defaultdict(list)
    scorer_errors: dict[str, int] = defaultdict(int)
    judge_cost = 0.0
    first_fail: dict[tuple[str, str], str] = {}
    fail_count: dict[tuple[str, str], int] = defaultdict(int)
    for r in results:
        if r.error is not None:
            # One "agent error" row, not one identical row per scorer.
            key = (r.case_id, AGENT_ERROR)
            fail_count[key] += 1
            first_fail.setdefault(key, r.error)
        for sc in r.scores:
            stats[sc.scorer].append((sc.passed, sc.score))
            scorer_errors[sc.scorer] += bool(sc.details.get("scorer_error"))
            judge_cost += (sc.details.get("judge") or {}).get("cost_gbp", 0.0)
            if sc.passed is False and r.error is None:
                key = (r.case_id, sc.scorer)
                fail_count[key] += 1
                first_fail.setdefault(key, sc.explanation)

    scorers = []
    for name, rows in stats.items():
        applied = [(p, s) for p, s in rows if p is not None]
        numbers = [s for _p, s in applied if s is not None]
        n_pass = sum(1 for p, _s in applied if p)
        scorers.append(
            ScorerStats(
                scorer=name,
                scored=len(applied),
                passed=n_pass,
                skipped=len(rows) - len(applied) - scorer_errors[name],
                errors=scorer_errors[name],
                pass_rate=_rate(n_pass, len(applied)),
                mean_score=sum(numbers) / len(numbers) if numbers else None,
            )
        )

    tag_cases: dict[str, set[str]] = defaultdict(set)
    for c in run_cases:
        for tag in c.tags:
            tag_cases[tag].add(c.case_id)
    tags = []
    for tag in sorted(tag_cases):
        outs = [o for cid in tag_cases[tag] for o in by_case[cid] if o is not None]
        tags.append(
            TagStats(
                tag=tag,
                cases=len(tag_cases[tag]),
                attempts=len(outs),
                passed=sum(outs),
                pass_rate=_rate(sum(outs), len(outs)),
            )
        )

    attempts_per_case = {cid: len(v) for cid, v in by_case.items()}
    failures = [
        Failure(
            case_id=cid,
            scorer=scorer,
            failed=fail_count[(cid, scorer)],
            attempts=attempts_per_case[cid],
            explanation=first_fail[(cid, scorer)],
        )
        for cid, scorer in first_fail
    ]

    costs = [r.cost_gbp for r in results if r.cost_gbp is not None]
    judged_attempts = [o for o in outcome.values() if o is not None]
    return Report(
        run_id=run.id,
        suite=run.suite,
        agent=run.agent,
        k=run.k,
        status=run.status,
        git_commit=run.git_commit,
        git_dirty=run.git_dirty,
        config_hash=run.config_hash,
        dyno_version=run.dyno_version,
        started_at=run.started_at,
        finished_at=run.finished_at,
        cases=len(run_cases),
        attempts=len(results),
        errors=sum(1 for r in results if r.error is not None),
        attempts_passed=sum(judged_attempts),
        attempt_pass_rate=_rate(sum(judged_attempts), len(judged_attempts)),
        pass_at_k=_rate(sum(1 for cr in judged if cr.pass_at_k), len(judged)),
        pass_hat_k=_rate(sum(1 for cr in judged if cr.pass_hat_k), len(judged)),
        flaky=[cr.case_id for cr in reliability if cr.flaky],
        cost_gbp=sum(costs) if costs else None,
        cost_per_attempt_gbp=sum(costs) / len(costs) if costs else None,
        judge_cost_gbp=judge_cost,
        input_tokens=sum(r.input_tokens or 0 for r in results),
        output_tokens=sum(r.output_tokens or 0 for r in results),
        latency_p50_s=_seconds(_percentile([r.latency_ms for r in results], 0.5)),
        latency_p95_s=_seconds(_percentile([r.latency_ms for r in results], 0.95)),
        scorers=scorers,
        tags=tags,
        reliability=reliability,
        failures=failures,
    )


def _seconds(ms: float | None) -> float | None:
    return None if ms is None else ms / 1000


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def _num(x: float | None, fmt: str = ".2f") -> str:
    return "n/a" if x is None else format(x, fmt)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def to_markdown(r: Report) -> str:
    commit = (
        "n/a" if r.git_commit is None else r.git_commit[:7] + (" (dirty)" if r.git_dirty else "")
    )
    lines = [
        f"# Dyno report: {r.suite}",
        "",
        f"Run `{r.run_id}`, agent `{r.agent}`, k={r.k}, status {r.status}, "
        f"commit {commit}, config `{r.config_hash}`, {r.started_at:%Y-%m-%d %H:%M} UTC",
        "",
        "## Summary",
        "",
        "| Cases | Attempts | Errors | Attempt pass rate | pass@k | pass^k | Flaky |",
        "|---|---|---|---|---|---|---|",
        f"| {r.cases} | {r.attempts} | {r.errors} | {_pct(r.attempt_pass_rate)} | "
        f"{_pct(r.pass_at_k)} | {_pct(r.pass_hat_k)} | {len(r.flaky)} |",
        "",
        f"Cost: GBP {_num(r.cost_gbp, '.6f')} total, GBP {_num(r.cost_per_attempt_gbp, '.6f')} "
        f"per attempt (agent), GBP {r.judge_cost_gbp:.6f} judges, "
        f"tokens {r.input_tokens} in / {r.output_tokens} out, "
        f"latency p50 {_num(r.latency_p50_s, '.1f')}s, p95 {_num(r.latency_p95_s, '.1f')}s",
        "",
        "## Scorers",
        "",
        "| Scorer | Pass rate | Passed / scored | Mean score | Not applicable | Scorer errors |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {s.scorer} | {_pct(s.pass_rate)} | {s.passed}/{s.scored} | "
        f"{_num(s.mean_score)} | {s.skipped} | {s.errors} |"
        for s in r.scorers
    ]
    if r.tags:
        lines += ["", "## By tag", "", "| Tag | Cases | Pass rate |", "|---|---|---|"]
        lines += [f"| {t.tag} | {t.cases} | {_pct(t.pass_rate)} |" for t in r.tags]
    if r.flaky:
        lines += ["", "## Flaky cases", ""]
        lines += [
            f"- `{cr.case_id}`: {cr.passed}/{cr.attempts} passed"
            for cr in r.reliability
            if cr.flaky
        ]
    lines += ["", "## Failures", ""]
    if r.failures:
        lines += ["| Case | Scorer | Failed | Why (first failure) |", "|---|---|---|---|"]
        lines += [
            f"| `{f.case_id}` | {f.scorer} | {f.failed}/{f.attempts} | {_cell(f.explanation)} |"
            for f in r.failures
        ]
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"
