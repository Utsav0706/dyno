"""Import, labelling (simulated keypresses) and calibration."""

import pytest
from typer.testing import CliRunner

from conftest import EXAMPLE_SUITE
from dyno.agents.example import ExampleAgent
from dyno.calibration import calibrate, cohen_kappa, to_markdown
from dyno.cases import load_suite
from dyno.cli import app
from dyno.config import get_settings
from dyno.labelling import all_labels, claim_items, excerpt, save_label, task_items
from dyno.runner import run_suite
from dyno.scoring import Score
from dyno.store import Store, open_engine
from dyno.store.transfer import import_runs

runner = CliRunner()
JUDGE = {"model": "claude-haiku-5-5", "prompt": "judge_task_v1:abcd1234", "cost_gbp": 0.0}


def test_kappa():
    assert cohen_kappa([(True, True), (False, False)] * 5) == pytest.approx(1.0)
    # 50% agreement when each side says pass half the time = chance: kappa 0
    assert cohen_kappa([(True, True), (True, False), (False, True), (False, False)]) == 0
    # always "pass" on 9 passes and 1 fail: 90% agreement, kappa 0 (knows nothing)
    assert cohen_kappa([(True, True)] * 9 + [(False, True)]) == pytest.approx(0.0)
    assert cohen_kappa([(True, True)] * 4) is None  # one verdict throughout
    assert cohen_kappa([]) is None


def judged_run(store: Store) -> str:
    """The example suite with fake judge scores: task_rubric fails where the example
    agent fails; hallucination with two claims per attempt."""
    s = run_suite(load_suite(EXAMPLE_SUITE), ExampleAgent(), agent_name="example", k=1, store=store)
    run = store.get_run(s.run_id)
    for r in run.results:
        ok = r.case_id.startswith(("math", "fact-capital"))
        store.replace_scores(
            r.id,
            {
                "task_rubric": Score(
                    score=float(ok),
                    passed=ok,
                    explanation=f"judge says {ok}",
                    details={"judge": JUDGE},
                ),
                "hallucination": Score(
                    score=1.0,
                    passed=True,
                    details={
                        "judge": JUDGE,
                        "claims": [
                            {
                                "claim": f"{r.case_id} fact",
                                "meta": False,
                                "supported": ok,
                                "evidence": "E1" if ok else "",
                            },
                            {
                                "claim": "The sources do not say",
                                "meta": True,
                                "supported": True,
                                "evidence": "",
                            },
                        ],
                    },
                ),
            },
        )
    return s.run_id


def test_task_sample_has_all_fails_and_is_stable(store):
    judged_run(store)
    first = task_items(store, None, 4)
    assert len(first) == 4
    assert {"fact-unknown", "fact-step-budget", "agent-crash"} <= {i.case_id for i in first}
    assert [i.result_id for i in task_items(store, None, 4)] == [i.result_id for i in first]
    save_label(store, first[0].result_id, "task_rubric", True)
    assert first[0].result_id not in {i.result_id for i in task_items(store, None, 4)}


def test_claim_items_skip_meta_and_show_evidence(store):
    judged_run(store)
    items = claim_items(store, None, 30)
    assert items and all(i.claim != "The sources do not say" for i in items)
    math = next(i for i in items if i.case_id == "math-add")
    assert math.excerpts == ["[E1] (calculator) 42"]  # the passage the judge cited


def test_excerpt_finds_the_matching_window():
    passage = "x " * 2000 + "The London cap is GBP 190 per night." + " y" * 2000
    assert "GBP 190" in excerpt(passage, "London hotel cap GBP 190")


def test_calibrate_reports_kappa_and_disagreements(store):
    judged_run(store)
    items = task_items(store, None, 6)
    for item in items:
        human = item.case_id.startswith(("math", "fact-capital")) or item.case_id == "agent-crash"
        save_label(
            store,
            item.result_id,
            "task_rubric",
            human,
            note="crash counts" if item.case_id == "agent-crash" else "",
        )
    save_label(store, items[0].result_id, "quality", None)  # unsure: left out
    (quality, task) = calibrate(all_labels(store))
    assert (task.scorer, task.n, task.unsure) == ("task_rubric", 6, 0)
    assert task.matrix == [[3, 1], [0, 2]]
    assert task.kappa == pytest.approx((5 / 6 - 0.5) / 0.5)
    (d,) = task.disagreements
    assert d.case_id == "agent-crash" and d.note == "crash counts"
    assert quality.unsure == 1 and quality.n == 0 and quality.kappa is None
    md = to_markdown([quality, task])
    assert "| task_rubric | 6 | 83% | 0.67 | trusted |" in md


def test_claim_labels_calibrate_and_go_stale(store):
    judged_run(store)
    for item in claim_items(store, None, 30):
        save_label(store, item.result_id, "hallucination", True, item=item.claim)
    (h,) = calibrate(all_labels(store))
    assert h.n == 6 and len(h.disagreements) == 3  # judge said unsupported on 3
    save_label(
        store, item.result_id, "hallucination", True, item="a claim the judge no longer lists"
    )
    (h,) = calibrate(all_labels(store))
    assert h.stale == 1


def test_import_copies_runs_once(tmp_path, store):
    other_url = f"sqlite:///{(tmp_path / 'other.db').as_posix()}"
    other = Store(open_engine(other_url))
    run_id = judged_run(other)
    item = task_items(other, None, 1)[0]
    save_label(other, item.result_id, "task_rubric", False)
    run_suite(load_suite(EXAMPLE_SUITE), ExampleAgent(), agent_name="example", k=1, store=store)

    assert import_runs(other_url, store) == ([run_id], [])
    assert import_runs(other_url, store) == ([], [run_id])
    copied = store.get_run(run_id)
    source = other.get_run(run_id)
    assert len(copied.results) == 6
    for mine, theirs in zip(copied.results, source.results, strict=True):
        assert [s.scorer for s in mine.scores] == [s.scorer for s in theirs.scores]
        assert [(s.idx, s.name) for s in mine.steps] == [(s.idx, s.name) for s in theirs.steps]
    (lab,) = all_labels(store)
    assert lab.result.run_id == run_id and lab.result.case_id == item.case_id


# --- CLI ---


def _cli(monkeypatch, db_url, args, input=None):
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    try:
        return runner.invoke(app, args, input=input)
    finally:
        get_settings.cache_clear()


def test_label_session_saves_and_resumes(monkeypatch, db_url, store):
    judged_run(store)
    # item 1: bad key then y, quality n, note; item 2: skip; item 3: quit
    result = _cli(
        monkeypatch, db_url, ["label", "task", "--n", "3"], input="x\ny\nn\nclear\ns\nq\n"
    )
    assert result.exit_code == 0, result.output
    assert "type one of" in result.output and "QUESTION" in result.output
    assert "judge says" not in result.output  # blind
    labels = {(lab.scorer, lab.label, lab.note) for lab in all_labels(store)}
    assert labels == {("task_rubric", True, "clear"), ("quality", False, "clear")}
    again = _cli(monkeypatch, db_url, ["label", "task", "--n", "6"], input="q\n")
    assert "[1/5]" in again.output  # the labelled one is not offered again


def test_label_claims_and_calibrate_cli(monkeypatch, db_url, store, tmp_path):
    judged_run(store)
    result = _cli(monkeypatch, db_url, ["label", "claims", "--n", "2"], input="y\n\nu\n\n")
    assert result.exit_code == 0, result.output and "CLAIM" in result.output
    out = tmp_path / "cal.md"
    cal = _cli(monkeypatch, db_url, ["calibrate", "--out", str(out)])
    assert cal.exit_code == 0 and "hallucination: 1 labels" in cal.output
    assert "# Judge calibration" in out.read_text(encoding="utf-8")


def test_calibrate_without_labels(monkeypatch, db_url):
    assert _cli(monkeypatch, db_url, ["calibrate"]).exit_code == 1


def test_import_cli(monkeypatch, db_url, tmp_path):
    other = tmp_path / "other.db"
    run_id = judged_run(Store(open_engine(f"sqlite:///{other.as_posix()}")))
    result = _cli(monkeypatch, db_url, ["import", str(other)])
    assert result.exit_code == 0 and f"imported {run_id}" in result.output
