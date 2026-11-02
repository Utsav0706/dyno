# Dyno report: scout-golden

Run `12fbcb8b0759`, agent `scout`, k=3, status finished, commit 65186d3 (dirty), config `db145218898184c9`, 2026-11-02 19:47 UTC

## Summary

| Cases | Attempts | Errors | Attempt pass rate | pass@k | pass^k | Flaky |
|---|---|---|---|---|---|---|
| 10 | 30 | 0 | 30% | 50% | 20% | 3 |

Cost: GBP 0.742319 total, GBP 0.024744 per attempt (agent), GBP 0.085732 judges, tokens 2073472 in / 203719 out, latency p50 28.2s, p95 54.3s

## Scorers

| Scorer | Pass rate | Passed / scored | Mean score | Not applicable | Scorer errors |
|---|---|---|---|---|---|
| task_rubric | 47% | 14/30 | 0.67 | 0 | 0 |
| hallucination | 97% | 29/30 | 0.99 | 0 | 0 |
| quality | 33% | 10/30 | 0.51 | 0 | 0 |
| tool_correctness | 100% | 27/27 | 1.00 | 3 | 0 |
| trajectory_efficiency | 87% | 26/30 | 1.00 | 0 | 0 |
| cost_latency | n/a | 0/0 | n/a | 30 | 0 |

## By tag

| Tag | Cases | Pass rate |
|---|---|---|
| both | 4 | 0% |
| ci | 5 | 33% |
| docs | 1 | 33% |
| unanswerable | 1 | 100% |
| web | 4 | 42% |

## Flaky cases

- `docs-london-hotel-cap`: 1/3 passed
- `web-brexit-dates`: 1/3 passed
- `web-speed-of-light`: 1/3 passed

## Failures

| Case | Scorer | Failed | Why (first failure) |
|---|---|---|---|
| `web-minimum-wage-start` | task_rubric | 3/3 | The answer correctly gives the start date of 1 April 1999 but states that the starting adult hourly rate is not in the notes, so it omits the GBP 3.60 rate. It does not present a wrong figure, only admits the gap, and the later rates it cites are labelled as context. |
| `web-minimum-wage-start` | quality | 3/3 | 3.0/5 (correct 3, helpful 2, clear 4): The start date of 1 April 1999 is correctly given, but the answer omits the £3.60 starting adult rate that the reference provides, so it fails half the question. It is well organised and clearly states what the notes lack, though its sourcing is somewhat padded with later rates and an unrelated note. |
| `web-speed-of-light` | quality | 2/3 | 3.7/5 (correct 5, helpful 3, clear 3): The value 299 792 458 m/s and the reason it is exact (the metre is defined from c) match the reference and are stated correctly. However, the answer is padded with historical detail and internal source tags like [S6] and a 'Limitations' section about other sources, which obscures the direct answer. |
| `web-brexit-dates` | task_rubric | 2/3 | The answer does not give the UK's exit date of 31 January 2020, saying the notes do not state it. It gives 31 December 2020 only as the default end date and explicitly declines to confirm that the transition period actually ended then, so that key point is only hedged. |
| `web-brexit-dates` | quality | 2/3 | 2.0/5 (correct 2, helpful 1, clear 3): The answer fails to give the UK exit date (31 January 2020), which the reference includes, claiming the sources do not state it. It correctly gives the 31 December 2020 transition end, but the hedging about whether it actually ended and the unrelated 'no sources read' note add padding. |
| `docs-london-hotel-cap` | task_rubric | 2/3 | The answer key gives GBP 190 per night excluding breakfast, but the answer says the documents do not state a specific London hotel maximum and never mentions the GBP 190 figure. It fails to provide the key point, and while it does not state a conflicting figure, it does claim the policy has no hotel limits, which is inconsistent with the key. |
| `docs-london-hotel-cap` | quality | 2/3 | 1.3/5 (correct 1, helpful 1, clear 2): The reference gives GBP 190 per night for London, but the answer claims the documents contain no London hotel cap, so it fails the core question. It is also internally inconsistent, citing S1 page 2 for a GBP 190 figure while saying the notes lack it. |
| `both-ax7-battery-voltage` | task_rubric | 3/3 | The answer correctly identifies LiFePO4 chemistry (key point 1) but explicitly says the single-cell nominal voltage is not available, so the 3.2 V figure in key point 2 is not stated. It does not contradict the key and gives no specific cell voltage. |
| `both-ax7-battery-voltage` | quality | 3/3 | 2.7/5 (correct 2, helpful 2, clear 4): The answer correctly identifies LiFePO4 but fails to give the expected nominal cell voltage of about 3.2 V, claiming the sources don't state it, which contradicts the reference. It is well organised and clearly sourced, but the key part of the question goes unanswered. |
| `both-mileage-vs-hmrc` | hallucination | 1/3 | 2/7 claims unsupported: The Quillmere rates match HMRC's approved rates for cars and vans for tax year 2; The 25p rate over 10,000 miles in Quillmere's policy matches HMRC's 25p rate ove |
| `both-mileage-vs-hmrc` | quality | 2/3 | 2.0/5 (correct 2, helpful 2, clear 2): The answer correctly states Quillmere's 45p and 25p rates but misstates HMRC's approved rate as 25p-only for 2011 to 2026 and never clearly says the 45p rate was matched until 2025-26, contradicting the reference's 55p/25p framing for 2026-27. It also pads with irrelevant limitations about source labels and hidden text, making it harder to follow. |
| `both-mileage-vs-hmrc` | trajectory_efficiency | 2/3 | fetch_url repeated 3x with the same arguments |
| `both-daventry-county` | task_rubric | 3/3 | The answer correctly identifies the Daventry fulfilment site as the outage location (point 1) but fails to state that Daventry is in Northamptonshire, instead claiming the notes do not give the county and refusing to answer. It does not contradict the key, and it gives no specific county answer. |
| `both-daventry-county` | quality | 3/3 | 2.7/5 (correct 2, helpful 2, clear 4): The answer correctly identifies Daventry as the site and says the notes don't name the county, but the reference expects Northamptonshire, and the answer refuses to give it, so it fails to answer the question directly. It is well organised, though padded with unneeded citations and sections. |
| `both-daventry-county` | trajectory_efficiency | 1/3 | web_search repeated 3x with the same arguments |
| `both-company-size` | task_rubric | 3/3 | The answer correctly reports the GBP 23.4 million 2025 revenue forecast and the 212 headcount, and states the £15m and 50-employee limits. However, it wrongly concludes the size test cannot be settled without a balance sheet total. Since turnover and headcount both exceed the limits, Quillmere fails two of the three tests and is not small, so the answer misses the key conclusion. |
| `both-company-size` | quality | 3/3 | 2.7/5 (correct 2, helpful 3, clear 3): The answer correctly cites the small-company turnover and employee limits but then says the test cannot be settled, missing the reference's clear conclusion that Quillmere exceeds the turnover and headcount limits and is medium-sized. Its claim that the balance sheet total is needed is fair, but it is overcautious since two of three tests already fail, and it cites sources and figures not in the question or reference, which adds clutter and makes it harder to follow. |
| `both-company-size` | trajectory_efficiency | 1/3 | fetch_url repeated 3x with the same arguments |
