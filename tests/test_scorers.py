import pytest

from dyno.agent import Step
from dyno.cases import Case
from dyno.scoring import Attempt, Score, build_scorers, score_attempt
from dyno.scoring.cost import CostLatency
from dyno.scoring.task import TaskSuccess
from dyno.scoring.tools import ToolCorrectness
from dyno.scoring.trajectory import TrajectoryEfficiency


def case(**kw) -> Case:
    return Case(id="c", input="q", **kw)


def attempt(answer: str = "", steps: list[Step] | None = None, **kw) -> Attempt:
    return Attempt(final_answer=answer, steps=steps or [], **kw)


def call(name: str, **args) -> Step:
    return Step(type="tool_call", name=name, args=args)


# --- task_success ---


def test_contains_ignores_case_and_spacing():
    s = TaskSuccess().score(case(expected="Paris"), attempt("It is  PARIS."))
    assert s.passed and s.score == 1.0


def test_exact_ignores_trailing_punctuation_only():
    t = TaskSuccess("exact")
    assert t.score(case(expected="Paris."), attempt("paris")).passed
    assert not t.score(case(expected="Paris"), attempt("It is Paris")).passed


def test_regex_mode_and_case_override():
    s = TaskSuccess().score(case(expected=r"\b42\b", match="regex"), attempt("answer: 42"))
    assert s.passed and s.details["mode"] == "regex"


def test_key_points_score_share_found():
    s = TaskSuccess().score(case(expected=["1999", "3.60", "MPC"]), attempt("1999, GBP 3.60"))
    assert s.passed is False
    assert s.score == pytest.approx(2 / 3)
    assert s.details["missing"] == ["MPC"] and "missing: MPC" in s.explanation


@pytest.mark.parametrize("expected", [None, []])
def test_no_expected_is_not_applicable(expected):
    s = TaskSuccess().score(case(expected=expected), attempt("x"))
    assert s.passed is None and s.score is None


def answer_is_upper(case, attempt):
    return attempt.final_answer.isupper()


def custom_score(case, attempt):
    return Score(score=0.5, passed=True, explanation="half")


def test_custom_check_bool_and_score():
    t = TaskSuccess()
    assert t.score(case(check="test_scorers:answer_is_upper"), attempt("OK")).passed
    assert not t.score(case(check="test_scorers:answer_is_upper"), attempt("ok")).passed
    s = t.score(case(check="test_scorers:custom_score"), attempt("x"))
    assert s.score == 0.5 and s.explanation == "half"


def test_bad_mode_rejected():
    with pytest.raises(TypeError):
        TaskSuccess("fuzzy")  # type: ignore[arg-type]


# --- tool_correctness ---


def test_tools_missing_and_forbidden():
    s = ToolCorrectness().score(
        case(must_call=["search", "read"], must_not_call=["delete"]),
        attempt(steps=[call("search"), call("delete")]),
    )
    assert s.passed is False and s.score == pytest.approx(1 / 3)
    assert s.explanation == "did not call read; called delete"
    assert s.details["called"] == {"search": 1, "delete": 1}


def test_tools_kept_and_not_applicable():
    t = ToolCorrectness()
    assert t.score(case(must_call=["search"]), attempt(steps=[call("search")])).passed
    assert t.score(case(), attempt()).passed is None


def test_tool_results_do_not_count_as_calls():
    s = ToolCorrectness().score(
        case(must_call=["search"]), attempt(steps=[Step(type="tool_result", name="search")])
    )
    assert s.passed is False


# --- trajectory_efficiency ---


def test_budget_counts_calls_not_results():
    steps = [
        Step(type="llm_call", name="m"),
        call("search", q="a"),
        Step(type="tool_result", name="search"),
        Step(type="llm_call", name="m"),
    ]
    t = TrajectoryEfficiency()
    assert t.score(case(max_steps=3), attempt(steps=steps)).passed
    over = t.score(case(max_steps=2), attempt(steps=steps))
    assert over.passed is False and over.score == pytest.approx(2 / 3)
    assert over.explanation.startswith("3 steps > max 2")


def test_loop_detection_needs_same_arguments():
    t = TrajectoryEfficiency()
    loop = t.score(case(), attempt(steps=[call("search", q="a")] * 3))
    assert loop.passed is False and loop.details["loops"] == {"search": 3}
    varied = [call("search", q=str(i)) for i in range(5)]
    assert t.score(case(), attempt(steps=varied)).passed
    assert (
        TrajectoryEfficiency(loop_threshold=5)
        .score(case(), attempt(steps=[call("search", q="a")] * 4))
        .passed
    )


# --- cost_latency ---


def priced(cost: float | None, ms: float) -> Attempt:
    return attempt(steps=[Step(type="llm_call", name="m", cost_gbp=cost)], latency_ms=ms)


def test_cost_is_information_without_limits():
    s = CostLatency().score(case(), priced(0.012, 2500))
    assert s.passed is None and s.explanation == "GBP 0.0120, 2.5s"
    assert s.details["cost_gbp"] == pytest.approx(0.012)


def test_cost_and_latency_limits():
    t = CostLatency(max_cost_gbp=0.01, max_latency_s=2)
    s = t.score(case(), priced(0.02, 3000))
    assert s.passed is False and "cost > GBP 0.01" in s.explanation and "time > 2" in s.explanation
    assert CostLatency(max_cost_gbp=0.05).score(case(), priced(0.02, 1)).passed


def test_unknown_cost_skips_cost_limit():
    assert CostLatency(max_cost_gbp=0.01).score(case(), priced(None, 10)).passed is None


# --- plumbing ---


def test_agent_error_fails_scorers_but_cost_still_reported():
    scorers = build_scorers([])
    scores = score_attempt(scorers, case(expected="x"), attempt(error="Boom", latency_ms=5))
    assert scores["task_success"].passed is False
    assert scores["task_success"].explanation == "agent error: Boom"
    assert scores["cost_latency"].passed is None  # information, from the real timing


def test_scorer_exception_is_a_scorer_error_not_a_fail():
    scores = score_attempt([TaskSuccess("regex")], case(expected="(unclosed"), attempt("anything"))
    assert scores["task_success"].passed is None
    assert scores["task_success"].details == {"scorer_error": True}


def test_build_scorers_specs():
    names = [s.name for s in build_scorers([])]
    assert names == ["task_success", "tool_correctness", "trajectory_efficiency", "cost_latency"]
    (cost,) = build_scorers([{"cost_latency": {"max_cost_gbp": 0.1}}])
    assert cost.max_cost_gbp == 0.1
    assert build_scorers([{"task_success": None}])[0].mode == "contains"


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        (["nope"], "unknown scorer"),
        ([{"cost_latency": {"max_cost": 1}}], "bad settings"),
        ([{"a": {}, "b": {}}], "exactly one name"),
    ],
)
def test_build_scorers_rejects_bad_specs(spec, message):
    with pytest.raises(ValueError, match=message):
        build_scorers(spec)
