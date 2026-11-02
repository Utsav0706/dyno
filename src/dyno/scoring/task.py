"""task_success: does the answer match `expected`?

Modes (suite default, a case can override with `match:`):
- contains (default): each expected text appears in the answer, ignoring case and
  extra whitespace.
- exact: the answer equals the expected text, ignoring case, whitespace and trailing
  punctuation.
- regex: each expected pattern is found with re.search (case-sensitive unless the
  pattern says (?i)).

A list of expected key points scores the share found and passes only if all are found.
Key points written as full sentences (as in Scout's golden set) rarely match word for
word; the rubric judge (M4) is the real task_success for those.

`check: package.module:function` replaces all of this with your own function. It gets
(case, attempt) and returns a bool or a Score.
"""

from __future__ import annotations

import re
from typing import ClassVar, get_args

from dyno._imports import load_attr
from dyno.cases import Case, MatchMode
from dyno.scoring.base import Attempt, Score, register


def _norm(text: str) -> str:
    return " ".join(text.casefold().split())


def matches(mode: MatchMode, expected: str, answer: str) -> bool:
    if mode == "contains":
        return _norm(expected) in _norm(answer)
    if mode == "exact":
        return _norm(expected).rstrip(".!?") == _norm(answer).rstrip(".!?")
    return re.search(expected, answer) is not None


@register("task_success")
class TaskSuccess:
    name: ClassVar[str]
    fails_on_error: ClassVar[bool] = True

    def __init__(self, mode: MatchMode = "contains") -> None:
        if mode not in get_args(MatchMode):
            raise TypeError(f"mode must be one of {get_args(MatchMode)}, got {mode!r}")
        self.mode = mode

    def score(self, case: Case, attempt: Attempt) -> Score:
        if case.check:
            out = load_attr(case.check)(case, attempt)
            if isinstance(out, Score):
                return out
            ok = bool(out)
            return Score(
                score=float(ok),
                passed=ok,
                explanation=f"{case.check} {'passed' if ok else 'failed'}",
            )

        expected = [case.expected] if isinstance(case.expected, str) else case.expected
        if not expected:
            return Score(explanation="no expected answer")

        mode = case.match or self.mode
        missing = [e for e in expected if not matches(mode, e, attempt.final_answer)]
        found = len(expected) - len(missing)
        if missing:
            shown = "; ".join(m[:80] for m in missing[:3])
            explanation = f"{mode}: {found}/{len(expected)} matched; missing: {shown}"
        else:
            explanation = f"{mode}: all {len(expected)} matched"
        return Score(
            score=found / len(expected),
            passed=not missing,
            explanation=explanation,
            details={"mode": mode, "missing": missing},
        )
