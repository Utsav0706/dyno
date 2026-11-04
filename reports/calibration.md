# Judge calibration

Cohen's kappa between the judge and hand labels. Bar: 0.6. The sample takes every item the judge failed plus a random share of the rest, so both verdicts are well represented (this raises the share of fails above the real rate). Labels marked unsure are left out.

| Judge | Labels | Agreement | Kappa | Verdict | Judged by |
|---|---|---|---|---|---|
| hallucination | 25 | 92% | 0.63 | trusted | claude-haiku-5-5 / judge_hallucination_v2:e93f65f2 |
| quality | 40 | 98% | 0.95 | trusted | claude-haiku-5-5 / judge_quality_v2:ab862f91 |
| task_rubric | 40 | 100% | 1.00 | trusted | claude-haiku-5-5 / judge_task_v1:9be1a1f1 |

## hallucination

| | judge pass | judge fail |
|---|---|---|
| **human pass** | 21 | 2 |
| **human fail** | 0 | 2 |

Unsure (left out): 5. No longer judged (left out): 0.

| Case | # | Item | Human | Judge | Judge's reason | Note |
|---|---|---|---|---|---|---|
| `both-mileage-vs-hmrc` | 1 | The 25p rate over 10,000 miles in Quillmere's policy matches HMRC's 25p rate over 10,000 miles. | pass | fail | judge cited: nothing | The policy and HMRC evidence both show 25p per mile above 10,000 miles. |
| `both-mileage-vs-hmrc` | 1 | The Quillmere rates match HMRC's approved rates for cars and vans for tax year 2011 to 2026. | pass | fail | judge cited: nothing | The evidence gives Quillmere’s 45p/25p policy and HMRC’s matching 45p/25p rates for 2011–2026. |

## quality

| | judge pass | judge fail |
|---|---|---|
| **human pass** | 16 | 0 |
| **human fail** | 1 | 23 |

Unsure (left out): 0. No longer judged (left out): 0.

| Case | # | Item | Human | Judge | Judge's reason | Note |
|---|---|---|---|---|---|---|
| `web-penicillin-discovery` | 1 |  | fail | pass | 4.0/5 (correct 4, helpful 4, clear 4): The answer correctly gives Fleming, 1928, and London, matching the reference, but it does not name St Mary's Hospital and instead says the building is unknown, which omits a reference key point. The rest is extra context that is well organised, though the lengt | Gives Fleming, 1928 and London, but omits St Mary’s Hospital. |

## task_rubric

| | judge pass | judge fail |
|---|---|---|
| **human pass** | 14 | 0 |
| **human fail** | 0 | 26 |

Unsure (left out): 0. No longer judged (left out): 0.
