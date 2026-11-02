import json

import pytest
from alembic import command
from sqlalchemy import text

from conftest import EXAMPLE_SUITE
from dyno.agent import AgentResult
from dyno.agents.example import ExampleAgent
from dyno.cases import Suite, load_suite
from dyno.report import AGENT_ERROR, Report, build_report, to_markdown
from dyno.runner import rescore_run, run_suite
from dyno.scoring.base import attempt_passed
from dyno.scoring.reliability import case_reliability
from dyno.store import Store, open_engine
from dyno.store.db import alembic_config


def test_attempt_passed_ignores_not_applicable():
    assert attempt_passed([True, None]) is True
    assert attempt_passed([True, False]) is False
    assert attempt_passed([None, None]) is None


def test_case_reliability():
    flaky = case_reliability("c", [True, False, None])
    assert (flaky.attempts, flaky.passed) == (2, 1)
    assert flaky.pass_at_k and not flaky.pass_hat_k and flaky.flaky
    solid = case_reliability("c", [True, True, True])
    assert solid.pass_hat_k and not solid.flaky
    assert case_reliability("c", [None]).pass_at_k is None


def test_example_report_numbers(store):
    s = run_suite(load_suite(EXAMPLE_SUITE), ExampleAgent(), agent_name="example", k=3, store=store)
    r = build_report(store.get_run(s.run_id))
    assert (r.cases, r.attempts, r.errors, r.attempts_passed) == (6, 18, 3, 9)
    assert r.pass_at_k == r.pass_hat_k == pytest.approx(0.5)  # deterministic: no flaky
    assert r.flaky == []
    by_name = {st.scorer: st for st in r.scorers}
    assert (by_name["task_success"].passed, by_name["task_success"].scored) == (12, 18)
    assert by_name["tool_correctness"].skipped == 3  # cases with no tool rules
    assert by_name["cost_latency"].scored == 0  # no limits set: information only
    assert {t.tag: t.pass_rate for t in r.tags}["math"] == 1.0

    failures = {(f.case_id, f.scorer) for f in r.failures}
    assert failures == {
        ("fact-unknown", "task_success"),
        ("fact-unknown", "tool_correctness"),
        ("fact-step-budget", "trajectory_efficiency"),
        ("agent-crash", AGENT_ERROR),  # one row, not one per scorer
    }

    md = to_markdown(r)
    assert "| 6 | 18 | 3 | 50% | 50% | 50% | 0 |" in md
    assert md.isascii()  # Windows consoles (cp1252) garble anything else
    assert Report.model_validate_json(r.model_dump_json()) == r


class FlakyAgent:
    """Right on every other call."""

    def __init__(self) -> None:
        self.calls = 0

    def run(self, input: str) -> AgentResult:
        self.calls += 1
        return AgentResult(final_answer="yes" if self.calls % 2 else "no")


def test_flaky_case_separates_pass_at_k_from_pass_hat_k(store):
    suite = Suite.model_validate({"cases": [{"id": "a", "input": "q", "expected": "yes"}]})
    s = run_suite(suite, FlakyAgent(), agent_name="flaky", k=3, store=store)
    r = build_report(store.get_run(s.run_id))
    assert (r.pass_at_k, r.pass_hat_k, r.flaky) == (1.0, 0.0, ["a"])
    assert "`a`: 2/3 passed" in to_markdown(r)


def test_rescore_uses_the_runs_scorer_settings(store):
    suite = Suite.model_validate(
        {
            "scorers": [{"task_success": {"mode": "exact"}}],
            "cases": [{"id": "a", "input": "capital of France", "expected": "Paris"}],
        }
    )
    s = run_suite(suite, ExampleAgent(), agent_name="example", k=1, store=store)
    with store.engine.begin() as conn:  # tamper, so rescoring visibly restores the score
        conn.execute(text("UPDATE scores SET passed = 0, explanation = 'tampered'"))
    assert rescore_run(store, s.run_id) == 1
    (row,) = store.get_run(s.run_id).results[0].scores
    assert (row.scorer, row.passed, row.explanation) == (
        "task_success",
        True,
        "exact: all 1 matched",
    )


def test_rescore_unknown_run(store):
    with pytest.raises(LookupError):
        rescore_run(store, "missing")


def test_upgrade_from_0001_keeps_data(db_url):
    """Runs stored by M1 survive migration 0002 (no table copy cascading deletes)."""
    from sqlalchemy import create_engine

    engine = create_engine(db_url)
    cfg = alembic_config(db_url)
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0001")
        conn.execute(
            text(
                "INSERT INTO runs VALUES ('r1','s','example',1,NULL,NULL,'h','0.1.0',"
                "'2026-11-02 00:00:00',NULL,'finished')"
            )
        )
        conn.execute(
            text("""INSERT INTO cases VALUES ('r1','a','2 + 2','"4"','[]','[]',NULL,'[]','[]')""")
        )
        conn.execute(
            text(
                "INSERT INTO results VALUES (1,'r1','a',1,'The answer is 4.',NULL,1.0,NULL,NULL,"
                "NULL,0,'{}','2026-11-02 00:00:00')"
            )
        )
    store = Store(open_engine(db_url))  # upgrades to head
    assert rescore_run(store, "r1") == 1
    run = store.get_run("r1")
    assert run.scorers is None and len(run.results) == 1
    assert {sc.scorer for sc in run.results[0].scores} >= {"task_success"}
    assert json.loads(build_report(run).model_dump_json())["attempts_passed"] == 1
