"""Run every case of a suite k times through an agent and store everything it did.

Cases run one after another, not in parallel: Scout allows only 2 running jobs per
user, and sequential runs keep latency numbers honest. An exception in one attempt is
stored as that attempt's error and the run carries on, so one crash doesn't throw away
a paid run.
"""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel

from dyno import __version__
from dyno.agent import Agent, AgentResult
from dyno.cases import Suite
from dyno.scoring import Attempt, Score, Scorer, attempt_passed, build_scorers, score_attempt
from dyno.store import Store
from dyno.store.db import attempt_from_row, case_from_row

log = logging.getLogger(__name__)


class RunSummary(BaseModel):
    run_id: str
    suite: str
    agent: str
    k: int
    cases: int
    attempts: int
    errors: int
    passed: int  # attempts where every applicable scorer passed
    input_tokens: int
    output_tokens: int
    cost_gbp: float
    seconds: float


# Called after each attempt: (case_id, attempt, result, latency_ms, scores).
OnAttempt = Callable[[str, int, AgentResult, float, dict[str, Score]], None]


def git_state() -> tuple[str | None, bool | None]:
    """HEAD commit and whether the working tree has uncommitted changes (None outside git).

    Read from the current directory: run Dyno from the repo whose change you're testing.
    """
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None, None
    return commit, bool(status.strip())


def run_suite(
    suite: Suite,
    agent: Agent,
    *,
    agent_name: str,
    k: int,
    store: Store,
    scorers: list[Scorer] | None = None,
    on_attempt: OnAttempt | None = None,
) -> RunSummary:
    """Run, score and store every attempt. Scorers default to the suite's list; they're
    built before the first agent call, so a typo in a scorer name costs nothing."""
    if scorers is None:
        scorers = build_scorers(suite.scorers)
    run_id = uuid.uuid4().hex[:12]
    commit, dirty = git_state()
    store.start_run(
        run_id=run_id,
        suite=suite.name,
        agent=agent_name,
        k=k,
        git_commit=commit,
        git_dirty=dirty,
        config_hash=suite.config_hash(agent_name, k),
        dyno_version=__version__,
        cases=suite.cases,
        scorers=suite.scorers,
    )
    log.info("run started", extra={"run_id": run_id, "suite": suite.name, "k": k})

    t0 = time.perf_counter()
    errors = passed = in_tok = out_tok = 0
    cost = 0.0
    try:
        for case in suite.cases:
            for attempt in range(1, k + 1):
                started = datetime.now(UTC)
                a0 = time.perf_counter()
                try:
                    result = agent.run(case.input)
                except Exception as exc:  # any agent failure is data, not a crash
                    # INFO, not WARNING: the error is stored and shown in progress already;
                    # the traceback is for LOG_LEVEL=INFO when debugging an adapter.
                    log.info(
                        "agent raised",
                        extra={"case_id": case.id, "attempt": attempt},
                        exc_info=True,
                    )
                    result = AgentResult(error=f"{type(exc).__name__}: {exc}")
                latency_ms = (time.perf_counter() - a0) * 1000
                scores = score_attempt(scorers, case, Attempt.from_result(result, latency_ms))

                store.save_result(
                    run_id=run_id,
                    case_id=case.id,
                    attempt=attempt,
                    result=result,
                    latency_ms=latency_ms,
                    started_at=started,
                    scores=scores,
                )
                errors += result.error is not None
                passed += bool(attempt_passed([sc.passed for sc in scores.values()]))
                in_tok += sum(s.input_tokens or 0 for s in result.steps)
                out_tok += sum(s.output_tokens or 0 for s in result.steps)
                cost += sum(s.cost_gbp or 0.0 for s in result.steps)
                if on_attempt:
                    on_attempt(case.id, attempt, result, latency_ms, scores)
    except BaseException:
        # Ctrl+C or a store failure: keep what was saved, mark the run as incomplete.
        store.finish_run(run_id, status="interrupted")
        raise
    store.finish_run(run_id)

    summary = RunSummary(
        run_id=run_id,
        suite=suite.name,
        agent=agent_name,
        k=k,
        cases=len(suite.cases),
        attempts=len(suite.cases) * k,
        errors=errors,
        passed=passed,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_gbp=cost,
        seconds=time.perf_counter() - t0,
    )
    log.info("run finished", extra=summary.model_dump())
    return summary


def rescore_run(store: Store, run_id: str, scorers: list[Scorer] | None = None) -> int:
    """Score a stored run again (same scorer settings as the run used, unless given).

    Free: it reads stored answers and steps, it never calls the agent. Returns the
    number of attempts scored.
    """
    run = store.get_run(run_id)
    if run is None:
        raise LookupError(f"no run {run_id!r}")
    if scorers is None:
        scorers = build_scorers(run.scorers or [])
    cases = {row.case_id: case_from_row(row) for row in run.cases}
    for result in run.results:
        scores = score_attempt(scorers, cases[result.case_id], attempt_from_row(result))
        store.replace_scores(result.id, scores)
    return len(run.results)
