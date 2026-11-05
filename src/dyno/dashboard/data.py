"""What the dashboard shows, as plain rows: no Streamlit here, so it is tested directly.

Every number comes from `build_report` and `compare_runs`, the same code behind
`dyno report` and `dyno compare`, so the dashboard and the CLI can't disagree.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from dyno.cluster import Clustering
from dyno.compare import case_status
from dyno.report import Report
from dyno.scoring.base import attempt_passed
from dyno.store.models import Result, Run


def run_row(rep: Report) -> dict[str, Any]:
    return {
        "run": rep.run_id,
        "started": rep.started_at,
        "suite": rep.suite,
        "agent": rep.agent,
        "k": rep.k,
        "cases": rep.cases,
        "attempts": rep.attempts,
        "pass rate": rep.attempt_pass_rate,
        "pass@k": rep.pass_at_k,
        "pass^k": rep.pass_hat_k,
        "flaky": len(rep.flaky),
        "agent GBP": rep.cost_gbp,
        "judge GBP": rep.judge_cost_gbp,
        "commit": (rep.git_commit or "")[:7],
        "status": rep.status,
    }


def trend_rows(reports: list[Report]) -> list[dict[str, Any]]:
    """One row per run and scorer (plus the attempt pass rate), oldest first."""
    rows = []
    for rep in sorted(reports, key=lambda r: r.started_at):
        label = f"{rep.started_at:%m-%d %H:%M} {rep.run_id[:6]}"
        rows.append({"run": label, "metric": "all scorers", "pass rate": rep.attempt_pass_rate})
        rows += [
            {"run": label, "metric": s.scorer, "pass rate": s.pass_rate}
            for s in rep.scorers
            if s.pass_rate is not None
        ]
    return rows


def scorer_rows(rep: Report) -> list[dict[str, Any]]:
    return [
        {
            "scorer": s.scorer,
            "pass rate": s.pass_rate,
            "passed": s.passed,
            "scored": s.scored,
            "mean score": s.mean_score,
            "not applicable": s.skipped,
            "scorer errors": s.errors,
        }
        for s in rep.scorers
    ]


def tag_rows(rep: Report) -> list[dict[str, Any]]:
    return [
        {"tag": t.tag, "cases": t.cases, "attempts": t.attempts, "pass rate": t.pass_rate}
        for t in rep.tags
    ]


def case_rows(run: Run, rep: Report) -> list[dict[str, Any]]:
    """One row per case: status across its attempts and which scorers it failed."""
    failed: dict[str, set[str]] = defaultdict(set)
    for r in run.results:
        if r.error is not None:
            failed[r.case_id].add("agent error")
        failed[r.case_id] |= {s.scorer for s in r.scores if s.passed is False}
    tags = {c.case_id: c.tags for c in run.cases}
    inputs = {c.case_id: c.input for c in run.cases}
    return [
        {
            "case": cr.case_id,
            "status": case_status(cr),
            "passed": f"{cr.passed}/{cr.attempts}",
            "failed scorers": ", ".join(sorted(failed[cr.case_id])),
            "tags": ", ".join(tags.get(cr.case_id, [])),
            "input": inputs.get(cr.case_id, ""),
        }
        for cr in rep.reliability
    ]


def attempts_of(run: Run, case_id: str) -> list[Result]:
    return sorted((r for r in run.results if r.case_id == case_id), key=lambda r: r.attempt)


def attempt_outcome(result: Result) -> bool | None:
    return attempt_passed([s.passed for s in result.scores])


def step_rows(result: Result) -> list[dict[str, Any]]:
    return [
        {
            "#": st.idx,
            "type": st.type,
            "name": st.name,
            "args": json.dumps(st.args, ensure_ascii=False)[:300],
            "output": (st.output or "")[:300],
            "tokens in": st.input_tokens,
            "tokens out": st.output_tokens,
            "GBP": st.cost_gbp,
            "ms": st.latency_ms,
        }
        for st in result.steps
    ]


def load_clusterings(folder: Path) -> list[tuple[Path, Clustering]]:
    """Every `dyno cluster --format json` file in a folder; other JSON is skipped."""
    found = []
    for path in sorted(folder.glob("*.json")):
        try:
            found.append((path, Clustering.model_validate_json(path.read_text(encoding="utf-8"))))
        except (ValidationError, ValueError, OSError):
            continue
    return found
