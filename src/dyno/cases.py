"""Test cases and suites, loaded from YAML.

A suite file is a list of cases plus optional defaults:

    name: scout-golden          # optional, defaults to the file name
    agent: scout                # optional, `dyno run --agent` overrides it
    k: 3                        # optional, `dyno run --k` overrides it
    scorers: [task_success]     # optional, used from M2
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

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    input: str = Field(min_length=1)
    # A reference answer, a list of key points a correct answer covers (Scout's golden
    # set), or nothing (e.g. "unanswerable" cases, judged by a scorer instead).
    expected: str | list[str] | None = None
    must_call: list[str] = []
    must_not_call: list[str] = []
    max_steps: int | None = Field(default=None, gt=0)
    tags: list[str] = []
    # Reference documents for the hallucination scorer (M4); optional.
    sources: list[str] = []


class Suite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    agent: str | None = None
    k: int = Field(default=1, gt=0)
    scorers: list[str] = []
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
