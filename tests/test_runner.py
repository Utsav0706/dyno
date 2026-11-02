import pytest

from conftest import EXAMPLE_SUITE
from dyno.agent import AgentResult, Step
from dyno.agents.example import ExampleAgent
from dyno.cases import Suite, load_suite
from dyno.runner import run_suite


def test_k_repeats_store_every_attempt(store):
    suite = load_suite(EXAMPLE_SUITE)
    seen = []
    s = run_suite(
        suite,
        ExampleAgent(),
        agent_name="example",
        k=3,
        store=store,
        on_attempt=lambda case_id, attempt, *_: seen.append((case_id, attempt)),
    )
    assert s.attempts == 18 and s.errors == 3  # agent-crash fails all 3 attempts
    assert seen[:3] == [("math-add", 1), ("math-add", 2), ("math-add", 3)]

    run = store.get_run(s.run_id)
    assert run.status == "finished" and run.finished_at is not None
    assert run.k == 3 and run.config_hash == suite.config_hash("example", 3)
    assert len(run.cases) == 6 and len(run.results) == 18

    crash = [r for r in run.results if r.case_id == "agent-crash"]
    assert all(r.error.startswith("RuntimeError") and r.n_steps == 0 for r in crash)

    first = run.results[0]
    assert first.final_answer == "The answer is 42."
    assert [st.idx for st in first.steps] == [0, 1, 2, 3]
    assert first.steps[1].args == {"expression": "17 + 25"}
    assert first.input_tokens == sum(st.input_tokens or 0 for st in first.steps)


class CostlyAgent:
    def run(self, input: str) -> AgentResult:
        return AgentResult(
            final_answer="ok",
            steps=[
                Step(type="llm_call", name="m", input_tokens=10, output_tokens=5, cost_gbp=0.01),
                Step(type="tool_call", name="t"),  # unknown cost stays None
            ],
            metadata={"job_id": "j1"},
        )


def test_totals_and_metadata(store):
    suite = Suite.model_validate({"cases": [{"id": "a", "input": "q"}]})
    s = run_suite(suite, CostlyAgent(), agent_name="costly", k=2, store=store)
    assert (s.input_tokens, s.output_tokens) == (20, 10)
    assert s.cost_gbp == pytest.approx(0.02)
    result = store.get_run(s.run_id).results[0]
    assert result.cost_gbp == pytest.approx(0.01)
    assert result.steps[1].cost_gbp is None
    assert result.meta == {"job_id": "j1"}


class InterruptingAgent:
    def run(self, input: str) -> AgentResult:
        raise KeyboardInterrupt


def test_interrupt_marks_run_and_reraises(store):
    suite = Suite.model_validate({"cases": [{"id": "a", "input": "q"}]})
    with pytest.raises(KeyboardInterrupt):
        run_suite(suite, InterruptingAgent(), agent_name="x", k=1, store=store)
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from dyno.store.models import Run

    with Session(store.engine) as s:
        assert s.scalars(select(Run.status)).one() == "interrupted"
