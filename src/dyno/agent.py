"""How any agent plugs into Dyno: one method, `run(input) -> AgentResult`.

`Agent` is a Protocol, not a base class: an adapter only needs the right method shape,
so it never has to import or inherit from Dyno (structural typing, checked by mypy/pyright
and by isinstance at runtime).
"""

from __future__ import annotations

import importlib
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

StepType = Literal["llm_call", "tool_call", "tool_result"]


class Step(BaseModel):
    """One thing the agent did, in order. Fields an adapter can't know stay None."""

    type: StepType
    name: str  # model name for llm_call, tool name for tool_call / tool_result
    args: dict[str, Any] = {}
    output: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    # GBP, because Scout and Gearbox both report GBP: adapters pass costs straight through.
    cost_gbp: float | None = None
    latency_ms: float | None = None


class AgentResult(BaseModel):
    final_answer: str = ""
    steps: list[Step] = []
    # Set by an adapter that caught its own failure (e.g. HTTP 500). The runner also
    # fills it when run() raises.
    error: str | None = None
    # Free-form facts about this attempt (e.g. the agent's own job id or git commit).
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Agent(Protocol):
    def run(self, input: str) -> AgentResult: ...


def _registry() -> dict[str, str]:
    # name -> "module:attribute". Strings, so an adapter's dependencies are only
    # imported when that adapter is used. Scout and Gearbox join in M3.
    return {"example": "dyno.agents.example:ExampleAgent"}


def get_agent(name: str) -> Agent:
    """Build an agent from a registered name or a "package.module:Attribute" path."""
    target = _registry().get(name, name)
    if ":" not in target:
        known = ", ".join(sorted(_registry()))
        raise ValueError(f"unknown agent {name!r}: use one of {known} or 'module:Attribute'")
    module_name, attr = target.split(":", 1)
    factory = getattr(importlib.import_module(module_name), attr)
    agent = factory()
    if not isinstance(agent, Agent):
        raise TypeError(f"{target} has no run(input) method")
    return agent
