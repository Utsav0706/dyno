"""Judge client and judge scorers against a fake Anthropic client (no network, no cost)."""

from types import SimpleNamespace

import pytest

from dyno.agent import Step
from dyno.cases import Case
from dyno.judge import Judge, JudgeError, cost_gbp, load_prompt, set_judge
from dyno.scoring import Attempt, build_scorers, score_attempt
from dyno.scoring.judges import (
    ClaimCheck,
    ClaimChecks,
    Hallucination,
    KeyPointGrade,
    Quality,
    QualityGrade,
    TaskGrade,
    TaskRubric,
)


class FakeMessages:
    def __init__(self, replies, stop_reason="end_turn"):
        self.replies = replies  # output model class -> parsed reply
        self.stop_reason = stop_reason
        self.requests: list[dict] = []

    def parse(self, **kw):
        self.requests.append(kw)
        return SimpleNamespace(
            usage=SimpleNamespace(input_tokens=10_000, output_tokens=1_000),
            stop_reason=self.stop_reason,
            parsed_output=self.replies.get(kw["output_format"]),
        )


@pytest.fixture
def fake():
    """Install a judge with a fake client; returns its FakeMessages."""
    messages = FakeMessages({})
    set_judge(
        Judge(
            "claude-haiku-5-5",
            effort="medium",
            budget_gbp=1.0,
            client=SimpleNamespace(messages=messages),
        )
    )
    yield messages
    set_judge(None)


def answer(text="", steps=None):
    return Attempt(final_answer=text, steps=steps or [])


def task_grade(covered, contradicts=False, insufficient=False, specific=False):
    return TaskGrade(
        key_points=[KeyPointGrade(point=i, covered=c) for i, c in enumerate(covered, start=1)],
        contradicts_key=contradicts,
        states_insufficient_evidence=insufficient,
        gives_specific_answer=specific,
        reason="because",
    )


# --- judge client ---


def test_cost_in_gbp():
    assert cost_gbp("claude-haiku-5-5", 1_000_000, 0) == pytest.approx(0.079)
    assert cost_gbp("claude-sonnet-5-5", 0, 1_000_000) == pytest.approx(7.9)
    with pytest.raises(JudgeError, match="no price"):
        cost_gbp("claude-unknown", 1, 1)


def test_prompts_are_versioned():
    p = load_prompt("judge_task_v1")
    assert p.version.startswith("judge_task_v1:") and len(p.version) == len("judge_task_v1:") + 8
    with pytest.raises(ValueError):
        load_prompt("judge_nope_v9")


def test_request_shape_and_spend(fake):
    fake.replies[TaskGrade] = task_grade([True])
    TaskRubric().score(Case(id="c", input="q", expected="x"), answer("x"))
    req = fake.requests[0]
    assert req["model"] == "claude-haiku-5-5" and req["output_config"] == {"effort": "medium"}
    assert req["output_format"] is TaskGrade and req["system"].startswith("You grade")


def test_budget_stops_calls():
    messages = FakeMessages({TaskGrade: task_grade([True])})
    judge = Judge("claude-haiku-5-5", budget_gbp=0.001, client=SimpleNamespace(messages=messages))
    judge.ask(load_prompt("judge_task_v1"), "x", TaskGrade)  # GBP 0.00118 > budget
    with pytest.raises(JudgeError, match="budget used up"):
        judge.ask(load_prompt("judge_task_v1"), "x", TaskGrade)
    assert judge.calls == 1


def test_refusal_and_missing_parse_are_errors():
    for stop, replies in (("refusal", {TaskGrade: task_grade([True])}), ("end_turn", {})):
        judge = Judge(
            "claude-haiku-5-5", client=SimpleNamespace(messages=FakeMessages(replies, stop))
        )
        with pytest.raises(JudgeError):
            judge.ask(load_prompt("judge_task_v1"), "x", TaskGrade)


def test_missing_key_is_a_judge_error(monkeypatch, tmp_path):
    from dyno.config import get_settings

    monkeypatch.chdir(tmp_path)  # no .env here: a real key in dyno/.env must not leak in
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(JudgeError, match="ANTHROPIC_API_KEY"):
            Judge()
    finally:
        get_settings.cache_clear()


# --- task_rubric ---


def test_rubric_pass_rule_is_in_code(fake):
    case = Case(id="c", input="q", expected=["a", "b"])
    fake.replies[TaskGrade] = task_grade([True, False])
    s = TaskRubric().score(case, answer("a only"))
    assert (s.passed, s.score) == (False, 0.5)
    assert s.details["judge"]["prompt"].startswith("judge_task_v1:")
    fake.replies[TaskGrade] = task_grade([True, True], contradicts=True)
    assert TaskRubric().score(case, answer("a, b, but wrong")).passed is False
    fake.replies[TaskGrade] = task_grade([True, True, True])  # extra point numbers ignored
    assert TaskRubric().score(case, answer("a, b")).passed is True


def test_rubric_unanswerable(fake):
    case = Case(id="c", input="Who wins in 2029?", tags=["unanswerable"])
    fake.replies[TaskGrade] = task_grade([], insufficient=True)
    assert TaskRubric().score(case, answer("Can't be known yet.")).passed is True
    fake.replies[TaskGrade] = task_grade([], insufficient=True, specific=True)
    assert TaskRubric().score(case, answer("Unknown, but Alcaraz.")).passed is False
    assert "UNANSWERABLE" in fake.requests[-1]["messages"][0]["content"]


def test_rubric_not_applicable_and_empty_without_a_call(fake):
    assert TaskRubric().score(Case(id="c", input="q"), answer("x")).passed is None
    s = TaskRubric().score(Case(id="c", input="q", expected="x"), answer("  "))
    assert s.passed is False and s.explanation == "empty answer"
    assert fake.requests == []


# --- hallucination ---


def tool(name, output, ok=True):
    return [
        Step(type="tool_call", name=name),
        Step(type="tool_result", name=name, output=output, args={"ok": ok}),
    ]


def test_evidence_is_what_the_agent_received():
    h = Hallucination(exclude_tools=["save_note"], max_evidence_chars=100)
    steps = (
        tool("web_search", "NHS began 5 July 1948")
        + tool("save_note", "my note")  # the agent's own words: excluded
        + tool("fetch_url", "403 forbidden", ok=False)  # failed call: excluded
        + tool("rag_search", "x" * 200)  # over the cap: dropped
    )
    passages, dropped = h.evidence(
        Case(id="c", input="q", sources=["Doc text"]), answer("a", steps)
    )
    assert passages == ["[E1] Doc text", "[E2] (web_search) NHS began 5 July 1948"]
    assert dropped == 1


def test_hallucination_rate_and_threshold(fake):
    fake.replies[ClaimChecks] = ClaimChecks(
        claims=[
            ClaimCheck(claim="Launched 1948", supported=True, evidence="E1"),
            ClaimCheck(claim="Bevan led it", supported=True, evidence="E1"),
            ClaimCheck(claim="Cost GBP 1bn", supported=False, evidence=""),
        ]
    )
    attempt = answer("The NHS ...", tool("web_search", "evidence"))
    s = Hallucination().score(Case(id="c", input="q"), attempt)
    assert s.passed is False and s.score == pytest.approx(2 / 3)
    assert s.explanation.startswith("1/3 claims unsupported: Cost GBP 1bn")
    assert Hallucination(max_unsupported_rate=0.5).score(Case(id="c", input="q"), attempt).passed


def test_hallucination_not_applicable_without_evidence(fake):
    assert Hallucination().score(Case(id="c", input="q"), answer("391")).passed is None
    assert fake.requests == []


def test_no_claims_passes(fake):
    fake.replies[ClaimChecks] = ClaimChecks(claims=[])
    s = Hallucination().score(
        Case(id="c", input="q"), answer("I couldn't find it.", tool("t", "e"))
    )
    assert s.passed is True and s.explanation == "no factual claims"


# --- quality ---


def test_quality_mean_and_clamp(fake):
    fake.replies[QualityGrade] = QualityGrade(correct=5, helpful=4, clear=9, reason="good")
    s = Quality().score(Case(id="c", input="q", expected=["a"]), answer("a"))
    assert s.details["mean"] == pytest.approx(14 / 3)  # clear clamped to 5
    assert s.passed is True and "- a" in fake.requests[0]["messages"][0]["content"]
    fake.replies[QualityGrade] = QualityGrade(correct=3, helpful=4, clear=4, reason="meh")
    assert Quality().score(Case(id="c", input="q"), answer("x")).passed is False


# --- plumbing ---


def test_judge_failure_is_a_scorer_error_not_a_fail(fake):
    # fake has no reply for TaskGrade -> JudgeError inside the scorer
    scores = score_attempt([TaskRubric()], Case(id="c", input="q", expected="x"), answer("x"))
    s = scores["task_rubric"]
    assert s.passed is None and s.details == {"scorer_error": True}
    assert s.explanation.startswith("scorer error: JudgeError")


def test_judges_are_not_default_and_build_by_name():
    assert "task_rubric" not in [s.name for s in build_scorers([])]
    names = [s.name for s in build_scorers(["task_rubric", "hallucination", "quality"])]
    assert names == ["task_rubric", "hallucination", "quality"]
    with pytest.raises(ValueError):
        build_scorers([{"task_rubric": {"prompt": "judge_missing_v1"}}])
