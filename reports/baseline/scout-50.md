# Dyno report: scout-golden

Run `8c2395a69c09`, agent `scout`, k=1, status finished, commit 65186d3 (dirty), config `f03ac4633c32424d`, 2026-11-02 19:08 UTC

## Summary

| Cases | Attempts | Errors | Attempt pass rate | pass@k | pass^k | Flaky |
|---|---|---|---|---|---|---|
| 50 | 50 | 0 | 66% | 66% | 66% | 0 |

Cost: GBP 1.235868 total, GBP 0.024717 per attempt (agent), GBP 0.149351 judges, tokens 3521127 in / 350583 out, latency p50 30.5s, p95 62.3s

## Scorers

| Scorer | Pass rate | Passed / scored | Mean score | Not applicable | Scorer errors |
|---|---|---|---|---|---|
| task_rubric | 80% | 40/50 | 0.89 | 0 | 0 |
| hallucination | 98% | 49/50 | 0.99 | 0 | 0 |
| tool_correctness | 100% | 42/42 | 1.00 | 8 | 0 |
| trajectory_efficiency | 90% | 45/50 | 1.00 | 0 | 0 |
| cost_latency | n/a | 0/0 | n/a | 50 | 0 |
| quality | 82% | 41/50 | 0.78 | 0 | 0 |

## By tag

| Tag | Cases | Pass rate |
|---|---|---|
| both | 10 | 20% |
| ci | 5 | 60% |
| docs | 12 | 92% |
| unanswerable | 8 | 88% |
| web | 20 | 65% |

## Failures

| Case | Scorer | Failed | Why (first failure) |
|---|---|---|---|
| `web-minimum-wage-start` | task_rubric | 1/1 | The answer gives only the year 1999 and says the sources lack the exact start date (1 April 1999) and the adult rate (GBP 3.60). It does not state either key point, though it does not contradict the key and it correctly declines to give a specific figure for the starting rate. |
| `web-minimum-wage-start` | quality | 1/1 | 2.7/5 (correct 2, helpful 2, clear 4): The answer gives only the year 1999 and says the start date and the £3.60 starting adult rate are not in its sources, missing both reference key points. It is well organised and transparent about gaps, but it fails to provide the specific date and rate that were asked for. |
| `web-gdpr-article-17` | trajectory_efficiency | 1/1 | fetch_url repeated 4x with the same arguments |
| `web-transformer-paper` | trajectory_efficiency | 1/1 | fetch_url repeated 3x with the same arguments |
| `web-equality-act` | trajectory_efficiency | 1/1 | fetch_url repeated 3x with the same arguments |
| `web-london-underground-opening` | task_rubric | 1/1 | The answer gives the 10 January 1863 opening date, though it does not explicitly tie that railway to the London Underground name. It says the first section ran between Paddington and King's Cross, which conflicts with the key's Paddington to Farringdon route and does not state Farringdon. |
| `web-london-underground-opening` | quality | 1/1 | 2.7/5 (correct 2, helpful 3, clear 3): The answer gives the correct opening date and identifies the Metropolitan Railway, but says its first section ran Paddington to King's Cross, missing the reference's Paddington–Farringdon endpoint and contradicting it, and it hedges on linking the line to the London Underground. Organisation is readable but the limitations section adds clutter. |
| `web-ben-nevis-height` | task_rubric | 1/1 | The answer states Ben Nevis is 1,345m, matching key point 1, but does not give the feet equivalent (4,413 ft) and does not mention it is the highest mountain in the UK, so key point 2 is missing. Nothing contradicts the key. |
| `web-penicillin-discovery` | task_rubric | 1/1 | The answer credits Alexander Fleming with the discovery in 1928 and says it took place in London, which covers points 1 and 2. It explicitly says the notes do not identify the building, so it does not state St Mary's Hospital and point 3 is not covered. Nothing it says conflicts with the key. |
| `docs-incident-root-cause` | trajectory_efficiency | 1/1 | web_search repeated 4x with the same arguments |
| `both-ax7-battery-voltage` | task_rubric | 1/1 | The answer correctly identifies LiFePO4 as the AX-7 chemistry (point 1) but says the single-cell nominal voltage is not available from the sources, so it does not state the ~3.2 V figure (point 2 not covered). It does not contradict the key, and it does not present a wrong cell voltage. |
| `both-ax7-battery-voltage` | quality | 1/1 | 3.3/5 (correct 3, helpful 3, clear 4): The answer correctly identifies LiFePO4 chemistry but fails to give the reference's per-cell nominal voltage of about 3.2 V, saying it is unavailable, so a key point is missing. It is clearly organised with sources and limitations, though the extra pack-level detail is not asked for. |
| `both-iso-3691-4` | task_rubric | 1/1 | The answer key says the AX-7 is certified to ISO 3691-4, but the answer says the sources do not state the AX-7's certification and explicitly refuses to link ISO 3691-4 to the AX-7. It does correctly describe what ISO 3691-4 covers, matching key point 2, but it does not state key point 1 and does not contradict it. |
| `both-iso-3691-4` | quality | 1/1 | 2.0/5 (correct 1, helpful 2, clear 3): The reference says the AX-7 is certified to ISO 3691-4, but the answer claims no source states this, so it contradicts the key point; it also adds unrequested detail, though its structure is readable. |
| `both-mileage-vs-hmrc` | quality | 1/1 | 3.3/5 (correct 3, helpful 4, clear 3): The answer gives the right core conclusion (45p is below HMRC's 55p from 6 April 2026) and matches the reference, but it adds several unverified claims such as the retrospective change and the 21 May 2026 announcement, and its source-coverage and limitations sections are muddled and partly contradictory about what S1 and S2 say. |
| `both-daventry-county` | task_rubric | 1/1 | The answer correctly identifies the Daventry fulfilment site as the outage location (key point 1), but it explicitly states that the county is not answered by the sources, so it fails to give Northamptonshire (key point 2). It does not contradict the key. |
| `both-daventry-county` | quality | 1/1 | 1.7/5 (correct 1, helpful 1, clear 3): The reference says Daventry is in Northamptonshire, but the answer fails to give the county and wrongly claims the sources do not state it; the answer is also repetitive and cluttered. |
| `both-ax7-ip-rating` | task_rubric | 1/1 | The answer states the AX-7 is rated IP54, matching key point 1. It explicitly says the notes do not explain what the digits 5 and 4 mean, so it omits the dust protection meaning of 5 and the splashing-water meaning of 4. It does not state anything that conflicts with the key. |
| `both-ax7-ip-rating` | quality | 1/1 | 2.3/5 (correct 2, helpful 2, clear 3): The answer correctly reports IP54 from the spec but fails to explain what 5 and 4 mean, which the reference requires, and it wrongly claims the sources do not explain the digits and contradicts itself by saying the spec lacks a rating while citing it as listing IP54. |
| `both-singapore-cabin-class` | task_rubric | 1/1 | The answer correctly states the policy rule that premium economy applies to flights over 6 hours and economy to 6 hours or less, which covers key point 1. It does not state that a direct London to Singapore flight takes about 13 hours or conclude that premium economy is allowed, instead saying the duration cannot be confirmed, so key point 2 is not covered. |
| `both-singapore-cabin-class` | quality | 1/1 | 2.7/5 (correct 2, helpful 2, clear 4): The reference says a direct London to Singapore flight (about 13 hours) qualifies for premium economy, but the answer declines to conclude that, so it misses the key point. It is well organised and clearly sourced, though it leaves the user without the direct answer. |
| `both-leeds-population` | trajectory_efficiency | 1/1 | rag_search repeated 3x with the same arguments |
| `both-coventry-river` | task_rubric | 1/1 | The answer correctly states the AX-7 is assembled in Coventry, but it says the sources do not name the river through Coventry, so the River Sherbourne point is not covered. |
| `both-coventry-river` | quality | 1/1 | 2.7/5 (correct 2, helpful 2, clear 4): The answer correctly gives Coventry as the assembly city but wrongly says the sources do not name a river, missing the reference key point that the River Sherbourne flows through Coventry; the extra material on other sites is clearly organised but padding. |
| `none-fictional-company-revenue` | hallucination | 1/1 | 1/4 claims unsupported: Threnwick Quantasys Ltd is a Norwich photonics firm. |
