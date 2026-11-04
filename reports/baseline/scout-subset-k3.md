# Dyno report: scout-golden

Run `12fbcb8b0759`, agent `scout`, k=3, status finished, commit 65186d3 (dirty), config `db145218898184c9`, 2026-11-02 19:47 UTC

## Summary

| Cases | Attempts | Errors | Attempt pass rate | pass@k | pass^k | Flaky |
|---|---|---|---|---|---|---|
| 10 | 30 | 0 | 37% | 50% | 30% | 2 |

Cost: GBP 0.742319 total, GBP 0.024744 per attempt (agent), GBP 0.085938 judges, tokens 2073472 in / 203719 out, latency p50 28.2s, p95 54.3s

## Scorers

| Scorer | Pass rate | Passed / scored | Mean score | Not applicable | Scorer errors |
|---|---|---|---|---|---|
| task_rubric | 47% | 14/30 | 0.67 | 0 | 0 |
| hallucination | 97% | 29/30 | 0.99 | 0 | 0 |
| tool_correctness | 100% | 27/27 | 1.00 | 3 | 0 |
| trajectory_efficiency | 87% | 26/30 | 1.00 | 0 | 0 |
| cost_latency | n/a | 0/0 | n/a | 30 | 0 |
| quality | 43% | 13/30 | 0.57 | 0 | 0 |

## By tag

| Tag | Cases | Pass rate |
|---|---|---|
| both | 4 | 0% |
| ci | 5 | 33% |
| docs | 1 | 33% |
| unanswerable | 1 | 100% |
| web | 4 | 58% |

## Flaky cases

- `docs-london-hotel-cap`: 1/3 passed
- `web-brexit-dates`: 1/3 passed

## Failures

| Case | Scorer | Failed | Why (first failure) |
|---|---|---|---|
| `web-minimum-wage-start` | task_rubric | 3/3 | The answer correctly gives the start date of 1 April 1999 but states that the starting adult hourly rate is not in the notes, so it omits the GBP 3.60 rate. It does not present a wrong figure, only admits the gap, and the later rates it cites are labelled as context. |
| `web-minimum-wage-start` | quality | 3/3 | 2.7/5 (correct 2, helpful 2, clear 4): The start date of 1 April 1999 is given correctly, but the answer says the starting adult rate is unavailable, missing the reference's £3.60 key point, so it is incomplete. |
| `web-brexit-dates` | task_rubric | 2/3 | The answer does not give the UK's exit date of 31 January 2020, saying the notes do not state it. It gives 31 December 2020 only as the default end date and explicitly declines to confirm that the transition period actually ended then, so that key point is only hedged. |
| `web-brexit-dates` | quality | 2/3 | 2.3/5 (correct 2, helpful 2, clear 3): The answer correctly gives the transition period end as 31 December 2020 but fails to state the UK exit date of 31 January 2020, which the reference requires, claiming the sources do not contain it. It is organised clearly but the missing key point and extraneous limitations reduce usefulness. |
| `docs-london-hotel-cap` | task_rubric | 2/3 | The answer key gives GBP 190 per night excluding breakfast, but the answer says the documents do not state a specific London hotel maximum and never mentions the GBP 190 figure. It fails to provide the key point, and while it does not state a conflicting figure, it does claim the policy has no hotel limits, which is inconsistent with the key. |
| `docs-london-hotel-cap` | quality | 2/3 | 1.3/5 (correct 1, helpful 1, clear 2): The reference gives a GBP 190 per night London cap, but the answer says no London hotel limit exists and misses that figure, so it fails the core question despite being fairly organised. |
| `both-ax7-battery-voltage` | task_rubric | 3/3 | The answer correctly identifies LiFePO4 chemistry (key point 1) but explicitly says the single-cell nominal voltage is not available, so the 3.2 V figure in key point 2 is not stated. It does not contradict the key and gives no specific cell voltage. |
| `both-ax7-battery-voltage` | quality | 3/3 | 2.7/5 (correct 2, helpful 2, clear 4): The answer correctly identifies LiFePO4 but fails to give the reference's nominal cell voltage of about 3.2 V, saying it is unavailable from the sources. It is well organised and clearly cites its sources, but it leaves half the question unanswered. |
| `both-mileage-vs-hmrc` | hallucination | 1/3 | 2/7 claims unsupported: The Quillmere rates match HMRC's approved rates for cars and vans for tax year 2; The 25p rate over 10,000 miles in Quillmere's policy matches HMRC's 25p rate ove |
| `both-mileage-vs-hmrc` | trajectory_efficiency | 2/3 | fetch_url repeated 3x with the same arguments |
| `both-mileage-vs-hmrc` | quality | 2/3 | 2.7/5 (correct 2, helpful 3, clear 3): The answer correctly reports Quillmere's 45p/25p rates and that the 25p tier matches, but it claims HMRC's rates for 2011-2026 match, misses the reference's key point that 55p from 2026-27 is HMRC's first-tier rate that Quillmere's 45p falls below, and its direct answer is buried under source and limitation notes, with an apparent contradiction about whether the rates match. |
| `both-daventry-county` | task_rubric | 3/3 | The answer correctly identifies the Daventry fulfilment site as the outage location (point 1) but fails to state that Daventry is in Northamptonshire, instead claiming the notes do not give the county and refusing to answer. It does not contradict the key, and it gives no specific county answer. |
| `both-daventry-county` | trajectory_efficiency | 1/3 | web_search repeated 3x with the same arguments |
| `both-daventry-county` | quality | 3/3 | 2.7/5 (correct 2, helpful 2, clear 4): The reference says Daventry is in Northamptonshire, but the answer claims the notes don't give the county and refuses to answer, missing a key point; it is well organised but its refusal is not justified by the reference. |
| `both-company-size` | task_rubric | 3/3 | The answer correctly reports the GBP 23.4 million 2025 revenue forecast and the 212 headcount, and states the £15m and 50-employee limits. However, it wrongly concludes the size test cannot be settled without a balance sheet total. Since turnover and headcount both exceed the limits, Quillmere fails two of the three tests and is not small, so the answer misses the key conclusion. |
| `both-company-size` | quality | 2/3 | 3.0/5 (correct 2, helpful 3, clear 4): The answer correctly states the small company thresholds and cites the 212 headcount and 23.4m forecast, but it never reaches the reference's conclusion that Quillmere exceeds two of the three limits (turnover and employees) so is not small; it instead says the question is unsettled, which misses a key point and is less helpful than a direct answer. |
| `both-company-size` | trajectory_efficiency | 1/3 | fetch_url repeated 3x with the same arguments |
