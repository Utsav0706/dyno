"""Reliability across the k attempts of one case.

- pass@k: at least one attempt passed (could the agent do it?).
- pass^k: every attempt passed (can you rely on it?).
- flaky: some passed, some failed.

With exactly k attempts these are plain observed facts, so no estimator is needed
(the unbiased pass@k estimator matters only when sampling k of n > k attempts).
Attempts where no scorer applied are left out.
"""

from __future__ import annotations

from pydantic import BaseModel


class CaseReliability(BaseModel):
    case_id: str
    attempts: int  # attempts that had at least one applicable scorer
    passed: int
    pass_at_k: bool | None
    pass_hat_k: bool | None
    flaky: bool


def case_reliability(case_id: str, outcomes: list[bool | None]) -> CaseReliability:
    judged = [o for o in outcomes if o is not None]
    passed = sum(judged)
    if not judged:
        return CaseReliability(
            case_id=case_id, attempts=0, passed=0, pass_at_k=None, pass_hat_k=None, flaky=False
        )
    return CaseReliability(
        case_id=case_id,
        attempts=len(judged),
        passed=passed,
        pass_at_k=passed > 0,
        pass_hat_k=passed == len(judged),
        flaky=0 < passed < len(judged),
    )
