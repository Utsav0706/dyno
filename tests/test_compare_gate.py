"""compare, gate, cluster (fake embedder + fake judge) and import-failures."""

import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from conftest import EXAMPLE_SUITE
from dyno.agent import AgentResult
from dyno.agents.example import ExampleAgent
from dyno.cases import Suite, load_suite
from dyno.cli import app
from dyno.cluster import ClusterName, choose_k, cluster_failures, failed_attempts, to_markdown
from dyno.compare import compare_ids
from dyno.config import get_settings
from dyno.failures import ProductionFailure, case_id, read_failures, to_cases, write_cases
from dyno.gate import gate
from dyno.judge import Judge
from dyno.runner import run_suite

runner = CliRunner()


class Scripted:
    """Answers per question from a dict; anything else gets 'I don't know.'"""

    def __init__(self, answers):
        self.answers = answers

    def run(self, input: str) -> AgentResult:
        return AgentResult(final_answer=self.answers.get(input, "I don't know."))


SUITE = Suite.model_validate(
    {
        "scorers": ["task_success"],
        "cases": [
            {"id": "a", "input": "qa", "expected": "A"},
            {"id": "b", "input": "qb", "expected": "B"},
            {"id": "c", "input": "qc", "expected": "C"},
        ],
    }
)


def run(store, answers, suite=SUITE, k=1):
    return run_suite(suite, Scripted(answers), agent_name="scripted", k=k, store=store).run_id


def test_compare_finds_changes(store):
    before = run(store, {"qa": "A", "qb": "B"})
    after = run(store, {"qa": "A", "qc": "C"})
    c = compare_ids(store, before, after)
    assert c.same_config and c.common_cases == 3
    assert c.newly_failing == ["b"] and c.newly_passing == ["c"]
    assert c.metric("attempt_pass_rate").delta_pp == pytest.approx(0)


def test_compare_flaky_and_shared_cases_only(store):
    class Flaky:
        n = 0

        def run(self, input):
            self.n += 1
            return AgentResult(final_answer="A" if self.n % 2 else "no")

    before = run(
        store,
        {"qa": "A"},
        Suite.model_validate({"cases": [{"id": "a", "input": "qa", "expected": "A"}]}),
    )
    after = run_suite(SUITE, Flaky(), agent_name="flaky", k=2, store=store).run_id
    c = compare_ids(store, before, after)
    assert not c.same_config and c.common_cases == 1 and c.only_b == ["b", "c"]
    assert c.newly_flaky == ["a"]


def test_gate_rules(store):
    base = run(store, {"qa": "A", "qb": "B", "qc": "C"})
    worse = run(store, {"qa": "A", "qb": "B"})
    same = run(store, {"qa": "A", "qb": "B", "qc": "C"})
    bad = gate(worse, base, max_drop=2.0, store=store)
    assert not bad.passed and bad.drop_pp == pytest.approx(100 / 3)
    assert "dropped 33.3 pts" in bad.reason and bad.newly_failing == ["c"]
    assert gate(worse, base, max_drop=40, store=store).passed
    assert not gate(worse, base, max_drop=40, no_new_failures=True, store=store).passed
    assert gate(same, base, store=store).passed
    assert gate(same, base, metric="task_success", store=store).passed
    assert "unknown metric" in gate(same, base, metric="nope", store=store).reason


def test_gate_without_shared_cases(store):
    base = run(store, {}, Suite.model_validate({"cases": [{"id": "x", "input": "qx"}]}))
    other = run(store, {})
    result = gate(other, base, store=store)
    assert not result.passed and "share no cases" in result.reason
    with pytest.raises(LookupError):
        gate("nope", base, store=store)


# --- cluster ---


class FakeMessages:
    def __init__(self):
        self.n = 0

    def parse(self, **kw):
        self.n += 1
        return SimpleNamespace(
            usage=SimpleNamespace(input_tokens=1000, output_tokens=20),
            stop_reason="end_turn",
            parsed_output=ClusterName(name=f"group {self.n}"),
        )


def fake_embed(texts):
    """Two obvious groups: tool failures vs answer failures."""
    return [[1.0, 0.0] if "tool" in t else [0.0, 1.0] for t in texts]


def test_choose_k_and_small_inputs():
    labels, sil = choose_k([[0, 0], [0, 0.1], [5, 5], [5, 5.1], [0, 0.05]])
    assert len(set(labels)) == 2 and sil > 0.9
    assert choose_k([[0, 0], [1, 1]]) == ([0, 0], None)


def test_cluster_example_run(store):
    run_id = run_suite(
        load_suite(EXAMPLE_SUITE), ExampleAgent(), agent_name="example", k=1, store=store
    ).run_id
    the_run = store.get_run(run_id)
    items = failed_attempts([the_run])
    assert {i.case_id for i in items} == {"fact-unknown", "fact-step-budget", "agent-crash"}
    judge = Judge("claude-haiku-5-5", client=SimpleNamespace(messages=FakeMessages()))
    result = cluster_failures([the_run], embed=fake_embed, judge=judge)
    assert result.failures == 3 and result.k == 2
    assert sum(c.size for c in result.clusters) == 3 and result.judge_cost_gbp > 0
    assert "of failures" in to_markdown(result)
    only = failed_attempts([the_run], scorer="tool_correctness")
    assert [i.case_id for i in only] == ["fact-unknown", "agent-crash"]  # a crash fails it too


# --- import-failures ---


def test_failures_to_cases(tmp_path):
    lines = [
        {
            "input": "When did the NHS start?",
            "output": "1950",
            "reason": "wrong year",
            "source": "scout-feedback",
        },
        {"input": "  when did the NHS   start? ", "output": "dup"},  # same after normalising
        {
            "id": "pw 1/2",
            "input": "Price of AX-7?",
            "expected": ["GBP 41,500"],
            "tags": ["docs"],
            "extra": 1,
        },
        {"input": "Already covered"},
    ]
    path = tmp_path / "f.jsonl"
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n\n", encoding="utf-8")
    failures = read_failures(path)
    pairs, dropped = to_cases(failures, existing_inputs={"already covered"})
    assert dropped == 2
    nhs, ax7 = (c for c, _ in pairs)
    assert nhs.id == case_id(ProductionFailure(input="when did the nhs start?"))
    assert nhs.id.startswith("prod-") and nhs.tags == ["production", "scout-feedback"]
    assert (
        ax7.id == "pw-1-2" and ax7.expected == ["GBP 41,500"] and ax7.tags == ["production", "docs"]
    )

    out = tmp_path / "cases.yaml"
    write_cases(pairs, out)
    text = out.read_text(encoding="utf-8")
    assert "# was: 1950" in text and "# why: wrong year" in text
    suite = load_suite(_with_agent(tmp_path), out)
    assert [c.id for c in suite.cases] == [nhs.id, "pw-1-2"]


def _with_agent(tmp_path):
    p = tmp_path / "settings.yaml"
    p.write_text("agent: example\n", encoding="utf-8")
    return p


def test_bad_failure_line(tmp_path):
    path = tmp_path / "f.jsonl"
    path.write_text('{"output": "no input"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="f.jsonl:1"):
        read_failures(path)


# --- CLI ---


def _cli(monkeypatch, db_url, args):
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    try:
        return runner.invoke(app, args)
    finally:
        get_settings.cache_clear()


def test_compare_and_gate_cli(monkeypatch, db_url, store):
    base = run(store, {"qa": "A", "qb": "B", "qc": "C"})
    worse = run(store, {"qa": "A"})
    md = _cli(monkeypatch, db_url, ["compare", base, worse])
    assert md.exit_code == 0 and "## Newly failing (2)" in md.stdout
    js = _cli(monkeypatch, db_url, ["compare", base, worse, "--format", "json"])
    assert json.loads(js.stdout)["newly_failing"] == ["b", "c"]
    failed = _cli(monkeypatch, db_url, ["gate", worse, "--baseline", base])
    assert failed.exit_code == 1 and failed.stdout.startswith("FAIL")
    passed = _cli(monkeypatch, db_url, ["gate", base, "--baseline", base])
    assert passed.exit_code == 0 and passed.stdout.startswith("PASS")
    assert _cli(monkeypatch, db_url, ["compare", base, "nope"]).exit_code == 1


def test_import_failures_cli(monkeypatch, db_url, tmp_path):
    path = tmp_path / "f.jsonl"
    path.write_text('{"input": "What is 17 + 25?"}\n{"input": "New question"}\n', encoding="utf-8")
    out = tmp_path / "new.yaml"
    result = _cli(
        monkeypatch,
        db_url,
        ["import-failures", str(path), "--out", str(out), "--existing", str(EXAMPLE_SUITE)],
    )
    assert result.exit_code == 0 and "1 new cases" in result.stdout and "1 repeats" in result.stdout


def test_gate_on_one_scorer_judges_cases_by_that_scorer(store):
    """A case that only trips another scorer isn't 'newly failing' on task_success."""
    from dyno.agent import Step

    suite = Suite.model_validate(
        {
            "scorers": ["task_success", "tool_correctness"],
            "cases": [
                {"id": "a", "input": "qa", "expected": "A"},
                {"id": "b", "input": "qb", "expected": "B", "must_call": ["calc"]},
            ],
        }
    )

    class Agent:
        def __init__(self, use_tool):
            self.use_tool = use_tool

        def run(self, input):
            steps = [Step(type="tool_call", name="calc")] if self.use_tool else []
            return AgentResult(final_answer=input[1].upper(), steps=steps)

    base = run_suite(suite, Agent(True), agent_name="x", k=1, store=store).run_id
    cand = run_suite(suite, Agent(False), agent_name="x", k=1, store=store).run_id
    on_task = gate(cand, base, metric="task_success", no_new_failures=True, store=store)
    assert on_task.passed and on_task.newly_failing == []
    overall = gate(cand, base, max_drop=100, no_new_failures=True, store=store)
    assert not overall.passed and overall.newly_failing == ["b"]
    c = compare_ids(store, base, cand, scorer="task_success")
    assert c.cases_judged_by == "task_success" and c.newly_failing == []
