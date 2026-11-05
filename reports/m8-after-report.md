# Dyno report: scout-golden

Run `e7749253d38c`, agent `scout`, k=3, status finished, commit 05bbfde (dirty), config `db145218898184c9`, 2026-11-05 13:56 UTC

## Summary

| Cases | Attempts | Errors | Attempt pass rate | pass@k | pass^k | Flaky |
|---|---|---|---|---|---|---|
| 10 | 30 | 0 | 67% | 90% | 40% | 5 |

Cost: GBP 0.967292 total, GBP 0.032243 per attempt (agent), GBP 0.100337 judges, tokens 2581921 in / 271825 out, latency p50 46.2s, p95 62.3s

## Scorers

| Scorer | Pass rate | Passed / scored | Mean score | Not applicable | Scorer errors |
|---|---|---|---|---|---|
| task_rubric | 80% | 24/30 | 0.85 | 0 | 0 |
| hallucination | 100% | 30/30 | 1.00 | 0 | 0 |
| quality | 77% | 23/30 | 0.74 | 0 | 0 |
| tool_correctness | 100% | 27/27 | 1.00 | 3 | 0 |
| trajectory_efficiency | 87% | 26/30 | 1.00 | 0 | 0 |
| cost_latency | n/a | 0/0 | n/a | 30 | 0 |

## By tag

| Tag | Cases | Pass rate |
|---|---|---|
| both | 4 | 58% |
| ci | 5 | 73% |
| docs | 1 | 67% |
| unanswerable | 1 | 100% |
| web | 4 | 67% |

## Flaky cases

- `both-company-size`: 1/3 passed
- `both-daventry-county`: 2/3 passed
- `both-mileage-vs-hmrc`: 1/3 passed
- `docs-london-hotel-cap`: 2/3 passed
- `web-speed-of-light`: 2/3 passed

## Failures

| Case | Scorer | Failed | Why (first failure) |
|---|---|---|---|
| `web-minimum-wage-start` | task_rubric | 3/3 | The answer says the main adult hourly rate is not available and does not state GBP 3.60, so key point 2 is missed. It also does not identify 1 April 1999 as the start of the minimum wage; it lists commencement dates for sections of the Act, and mentions 1 April 1999 only in that context, so key point 1 is not clearly covered either. |
| `web-minimum-wage-start` | quality | 3/3 | 1.3/5 (correct 1, helpful 1, clear 2): The answer fails to give the start date as 1 April 1999 in the framing the reference expects and explicitly declines to state the main adult rate of GBP 3.60, which the reference lists as a key point, so it misses both required facts. |
| `web-speed-of-light` | trajectory_efficiency | 1/3 | fetch_url repeated 3x with the same arguments |
| `docs-london-hotel-cap` | task_rubric | 1/3 | The answer never states the GBP 190 per-night London cap; it instead claims the London maximum is not established by the material. Although it mentions a GBP 190 cap in its limitations section, it does not present that figure as the answer, so the key point is not covered and the answer does not clearly say the information is unavailable either. |
| `docs-london-hotel-cap` | quality | 1/3 | 1.3/5 (correct 1, helpful 1, clear 2): The answer claims the London hotel limit is not established, missing the reference's GBP 190 per night cap (excluding breakfast), so it fails the core question despite being organised. |
| `both-mileage-vs-hmrc` | quality | 1/3 | 3.3/5 (correct 2, helpful 4, clear 4): The answer gets the core comparison right (45p vs 55p for the first 10,000 miles, 25p matching) and is well organised, but it asserts HMRC rates matched for 2011 to 2026 and cites sources for claims beyond the reference; the 'matched until 2025-26' claim is consistent with the reference, yet the answer's 'AMAP increased in May 2026, retroactive' detail is unverifiable and the 'Source gaps' section contradicts the sourced HMRC claims it makes. |
| `both-mileage-vs-hmrc` | trajectory_efficiency | 2/3 | rag_search repeated 3x with the same arguments; fetch_url repeated 4x with the same arguments |
| `both-daventry-county` | trajectory_efficiency | 1/3 | web_search repeated 3x with the same arguments |
| `both-company-size` | task_rubric | 2/3 | The answer states the forecast revenue of GBP 23.4 million and headcount of 212, and lists the £15 million and 50-employee thresholds. It never concludes that Quillmere exceeds the small limits or is medium-sized, instead saying the question cannot be conclusively answered. |
| `both-company-size` | quality | 2/3 | 2.3/5 (correct 2, helpful 2, clear 3): The answer fails to reach the reference conclusion that Quillmere is not small: turnover of GBP 23.4m exceeds the GBP 15m limit and headcount of 212 exceeds 50, so it is medium-sized, yet it says the question cannot be conclusively answered. Its threshold explanation is clear and well organised, but the 'two of three' logic would still have allowed a clear answer from the two figures it had. |
