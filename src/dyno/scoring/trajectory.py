"""trajectory_efficiency: within the step budget, and no loops?

Steps counted against max_steps are llm_call and tool_call; a tool_result is the second
half of its call, so counting it too would charge every tool use twice.
A loop is the same tool called with the same arguments `loop_threshold` or more times.
Score = max_steps / steps taken (capped at 1), or 1 when there's no budget.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import ClassVar

from dyno.cases import Case
from dyno.scoring.base import Attempt, Score, register


@register("trajectory_efficiency")
class TrajectoryEfficiency:
    name: ClassVar[str]
    fails_on_error: ClassVar[bool] = True

    def __init__(self, loop_threshold: int = 3) -> None:
        if loop_threshold < 2:
            raise TypeError("loop_threshold must be at least 2")
        self.loop_threshold = loop_threshold

    def score(self, case: Case, attempt: Attempt) -> Score:
        taken = sum(1 for s in attempt.steps if s.type != "tool_result")
        calls = Counter(
            (s.name, json.dumps(s.args, sort_keys=True, default=str)) for s in attempt.tool_calls
        )
        loops = {name: n for (name, _args), n in calls.items() if n >= self.loop_threshold}

        problems = [f"{name} repeated {n}x with the same arguments" for name, n in loops.items()]
        budget = case.max_steps
        if budget is not None and taken > budget:
            problems.insert(0, f"{taken} steps > max {budget}")
        ratio = 1.0 if budget is None or taken == 0 else min(1.0, budget / taken)

        if problems:
            explanation = "; ".join(problems)
        elif budget is None:
            explanation = f"{taken} steps, no loops"
        else:
            explanation = f"{taken} steps <= max {budget}, no loops"
        return Score(
            score=ratio,
            passed=not problems,
            explanation=explanation,
            details={"steps": taken, "max_steps": budget, "loops": loops},
        )
