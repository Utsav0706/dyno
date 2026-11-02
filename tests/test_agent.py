import pytest

from dyno.agent import Agent, AgentResult, get_agent
from dyno.agents.example import ExampleAgent, calculate


def test_example_agent_satisfies_protocol():
    assert isinstance(ExampleAgent(), Agent)
    assert isinstance(get_agent("example"), ExampleAgent)


def test_calculator_path_is_deterministic():
    r1, r2 = ExampleAgent().run("What is 17 + 25?"), ExampleAgent().run("What is 17 + 25?")
    assert r1 == r2
    assert r1.final_answer == "The answer is 42."
    assert [(s.type, s.name) for s in r1.steps] == [
        ("llm_call", "example-model"),
        ("tool_call", "calculator"),
        ("tool_result", "calculator"),
        ("llm_call", "example-model"),
    ]
    assert r1.steps[1].args == {"expression": "17 + 25"}


def test_lookup_and_unknown():
    assert ExampleAgent().run("capital of Japan?").final_answer == "Tokyo."
    unknown = ExampleAgent().run("What is the capital of Peru?")
    assert unknown.final_answer == "I don't know."
    assert [s.type for s in unknown.steps] == ["llm_call"]


def test_calculate_is_safe():
    assert calculate("2 + 3 * 4") == 14
    assert calculate("-(1 - 4) / 2") == 1.5
    with pytest.raises(ValueError):
        calculate("__import__('os')")


def test_crash_input_raises():
    with pytest.raises(RuntimeError):
        ExampleAgent().run("crash please")


class DuckAgent:
    """Fits the protocol without importing or subclassing anything from Dyno's agent API."""

    def run(self, input: str) -> AgentResult:
        return AgentResult(final_answer=input.upper())


def test_import_path_agents():
    assert isinstance(get_agent("test_agent:DuckAgent"), DuckAgent)


def test_unknown_agent_and_wrong_shape():
    with pytest.raises(ValueError, match="unknown agent"):
        get_agent("nope")
    with pytest.raises(TypeError, match="no run"):
        get_agent("collections:OrderedDict")
