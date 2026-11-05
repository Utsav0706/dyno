"""The dashboard: its data rows directly, and the Streamlit app through AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import EXAMPLE_SUITE
from dyno.agents.example import ExampleAgent
from dyno.cases import load_suite
from dyno.cluster import Cluster, Clustering
from dyno.config import get_settings
from dyno.dashboard import data
from dyno.report import build_report
from dyno.runner import run_suite

APP = Path(__file__).resolve().parent.parent / "src" / "dyno" / "dashboard" / "app.py"


def example_run(store, k=2) -> str:
    suite = load_suite(EXAMPLE_SUITE)
    return run_suite(suite, ExampleAgent(), agent_name="example", k=k, store=store).run_id


def test_list_runs_newest_first(store):
    first, second = example_run(store, 1), example_run(store, 1)
    assert [r.id for r in store.list_runs()] == [second, first]


def test_rows(store):
    run = store.get_run(example_run(store))
    rep = build_report(run)
    row = data.run_row(rep)
    assert row["run"] == run.id and row["k"] == 2 and row["cases"] == 6
    trend = data.trend_rows([rep])
    assert trend[0]["metric"] == "all scorers"
    assert {t["metric"] for t in trend} >= {"task_success", "tool_correctness"}
    cases = {c["case"]: c for c in data.case_rows(run, rep)}
    assert cases["agent-crash"]["status"] == "fail"
    assert "agent error" in cases["agent-crash"]["failed scorers"]
    assert cases["fact-unknown"]["passed"] == "0/2"
    attempts = data.attempts_of(run, "math-add")
    assert [a.attempt for a in attempts] == [1, 2]
    assert data.attempt_outcome(attempts[0]) is True
    steps = data.step_rows(attempts[0])
    assert steps and steps[0]["#"] == 0


def test_load_clusterings_skips_other_json(tmp_path):
    good = Clustering(
        run_ids=["r1"],
        failures=2,
        k=1,
        silhouette=None,
        clusters=[Cluster(name="loops", size=2, share=1.0, case_ids=["a"], examples=["x"])],
        judge_cost_gbp=0.0,
    )
    (tmp_path / "c.json").write_text(good.model_dump_json(), encoding="utf-8")
    (tmp_path / "report.json").write_text('{"run_id": "r1"}', encoding="utf-8")
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    found = data.load_clusterings(tmp_path)
    assert [p.name for p, _ in found] == ["c.json"]


@pytest.fixture
def app(monkeypatch, db_url):
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    yield lambda: AppTest.from_file(str(APP), default_timeout=30)
    get_settings.cache_clear()


def test_app_empty_store(app):
    at = app().run()
    assert not at.exception
    assert "No runs yet" in at.info[0].value


def test_app_views(app, store, tmp_path):
    base, cand = example_run(store), example_run(store)
    at = app().run()
    assert not at.exception
    assert len(at.dataframe) == 1  # the runs table
    assert at.selectbox[0].value == "example"  # trend suite: the newest run's

    at.sidebar.radio[0].set_value("Run").run()
    assert not at.exception
    assert at.selectbox[0].value == cand  # newest run first
    assert [m.label for m in at.metric][:3] == ["Attempt pass rate", "pass@2", "pass^2"]

    at.session_state.case_id = "agent-crash"
    at.run()
    assert not at.exception
    assert any("agent-crash" in s.value for s in at.subheader)
    assert at.error[0].value  # the agent's error message
    assert any(t.label.startswith("Attempt 1") for t in at.tabs)

    at.sidebar.radio[0].set_value("Compare").run()
    assert not at.exception
    assert at.success[0].value.startswith("PASS")  # same agent, same answers

    folder = tmp_path / "clusters"
    folder.mkdir()
    at.sidebar.radio[0].set_value("Clusters").run()
    at.text_input[0].set_value(str(folder)).run()
    assert "No cluster files" in at.info[0].value
    clustering = Clustering(
        run_ids=[base],
        failures=3,
        k=1,
        silhouette=None,
        clusters=[Cluster(name="tool misuse", size=3, share=1.0, case_ids=["a"], examples=["e"])],
        judge_cost_gbp=0.0,
    )
    (folder / "c.json").write_text(clustering.model_dump_json(), encoding="utf-8")
    at.run()
    assert not at.exception
    assert at.expander[0].label.startswith("tool misuse")
