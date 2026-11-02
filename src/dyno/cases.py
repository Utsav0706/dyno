"""Test cases and suites, loaded from YAML.

A suite file is a list of cases plus optional defaults:

    name: scout-golden          # optional, defaults to the file name
    agent: scout                # optional, `dyno run --agent` overrides it
    k: 3                        # optional, `dyno run --k` overrides it
    scorers:                    # optional, default: all deterministic scorers
      - task_success: {mode: contains}
      - tool_correctness
      - cost_latency: {max_cost_gbp: 0.05}
    cases:
      - id: refund-policy-003
        input: Can I get a refund after 40 days?
        expected: No. Refund window is 30 days; offer store credit.
        must_call: [search_policy]
        must_not_call: [issue_refund]
        max_steps: 5
        tags: [policy, edge-case]

Unknown keys are errors (extra="forbid"): a typo such as `must_cal` would otherwise be
dropped silently and the case would pass for the wrong reason.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MatchMode = Literal["exact", "contains", "regex"]


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    input: str = Field(min_length=1)
    # A reference answer, a list of key points a correct answer covers (Scout's golden
    # set), or nothing (e.g. "unanswerable" cases, judged by a scorer instead).
    expected: str | list[str] | None = None

    @field_validator("expected", mode="before")
    @classmethod
    def _numbers_as_text(cls, v: Any) -> Any:
        # YAML reads `expected: 42` as an int; compare it as text like any answer.
        def text(x: Any) -> Any:
            return str(x) if isinstance(x, int | float) and not isinstance(x, bool) else x

        return [text(x) for x in v] if isinstance(v, list) else text(v)

    must_call: list[str] = []
    must_not_call: list[str] = []
    max_steps: int | None = Field(default=None, gt=0)
    tags: list[str] = []
    # Reference documents for the hallucination scorer (M4); optional.
    sources: list[str] = []
    # How task_success compares `expected` with the answer; None = the suite's setting.
    match: MatchMode | None = None
    # "package.module:function" for a custom task_success check (overrides `expected`).
    check: str | None = None


# A scorer by name, or {name: {params}}, e.g. {cost_latency: {max_cost_gbp: 0.05}}.
ScorerSpec = str | dict[str, dict[str, Any] | None]


class Suite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    agent: str | None = None
    k: int = Field(default=1, gt=0)
    # Empty = every deterministic scorer with default settings.
    scorers: list[ScorerSpec] = []
    cases: list[Case] = Field(min_length=1)

    @field_validator("cases")
    @classmethod
    def _unique_ids(cls, cases: list[Case]) -> list[Case]:
        ids = [c.id for c in cases]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate case ids: {sorted(dupes)}")
        return cases

    @model_validator(mode="after")
    def _overlap(self) -> Suite:
        for c in self.cases:
            both = set(c.must_call) & set(c.must_not_call)
            if both:
                raise ValueError(f"case {c.id}: {sorted(both)} in both must_call and must_not_call")
        return self

    def select(self, tags: list[str] | None = None, ids: list[str] | None = None) -> Suite:
        """The cases with any of `tags` and (if given) one of `ids`. Unknown ids are errors,
        so a typo can't silently shrink a run. The config hash then covers only these."""
        if ids:
            unknown = set(ids) - {c.id for c in self.cases}
            if unknown:
                raise ValueError(f"unknown case ids: {sorted(unknown)}")
        cases = [
            c
            for c in self.cases
            if (not ids or c.id in ids) and (not tags or set(tags) & set(c.tags))
        ]
        if not cases:
            raise ValueError(f"no cases match tags={tags} ids={ids}")
        return self.model_copy(update={"cases": cases})

    def config_hash(self, agent: str, k: int) -> str:
        """Fingerprint of what a run executes: the cases, scorers, agent and k.

        Two runs are only like-for-like when their hashes match, so compare/gate can warn.
        The suite name is left out: renaming a file doesn't change what was tested.
        """
        payload = self.model_dump(exclude={"name", "agent", "k"}) | {"agent": agent, "k": k}
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


def load_suite(path: str | Path) -> Suite:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping with a 'cases' list")
    data.setdefault("name", path.stem)
    return Suite.model_validate(data)
