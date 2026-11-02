"""tool_correctness: were the required tools called, and the forbidden ones not?

Score = share of must_call / must_not_call rules the attempt kept.
"""

from __future__ import annotations

from collections import Counter
from typing import ClassVar

from dyno.cases import Case
from dyno.scoring.base import Attempt, Score, register


@register("tool_correctness")
class ToolCorrectness:
    name: ClassVar[str]
    fails_on_error: ClassVar[bool] = True

    def score(self, case: Case, attempt: Attempt) -> Score:
        rules = len(case.must_call) + len(case.must_not_call)
        if not rules:
            return Score(explanation="no tool rules")

        called = Counter(s.name for s in attempt.tool_calls)
        missing = [t for t in case.must_call if t not in called]
        forbidden = [t for t in case.must_not_call if t in called]
        problems = [f"did not call {t}" for t in missing] + [f"called {t}" for t in forbidden]
        return Score(
            score=(rules - len(problems)) / rules,
            passed=not problems,
            explanation="; ".join(problems) or f"all {rules} tool rules kept",
            details={"called": dict(called), "missing": missing, "forbidden": forbidden},
        )
