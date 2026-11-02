# Dyno report: scout-golden

Run `8c2395a69c09`, agent `scout`, k=1, status finished, commit 65186d3 (dirty), config `f03ac4633c32424d`, 2026-11-02 19:08 UTC

## Summary

| Cases | Attempts | Errors | Attempt pass rate | pass@k | pass^k | Flaky |
|---|---|---|---|---|---|---|
| 50 | 50 | 0 | 40% | 40% | 40% | 0 |

Cost: GBP 1.235868 total, GBP 0.024717 per attempt (agent), GBP 0.149203 judges, tokens 3521127 in / 350583 out, latency p50 30.5s, p95 62.3s

## Scorers

| Scorer | Pass rate | Passed / scored | Mean score | Not applicable | Scorer errors |
|---|---|---|---|---|---|
| task_rubric | 80% | 40/50 | 0.89 | 0 | 0 |
| hallucination | 98% | 49/50 | 0.99 | 0 | 0 |
| quality | 54% | 27/50 | 0.68 | 0 | 0 |
| tool_correctness | 100% | 42/42 | 1.00 | 8 | 0 |
| trajectory_efficiency | 90% | 45/50 | 1.00 | 0 | 0 |
| cost_latency | n/a | 0/0 | n/a | 50 | 0 |

## By tag

| Tag | Cases | Pass rate |
|---|---|---|
| both | 10 | 20% |
| ci | 5 | 40% |
| docs | 12 | 67% |
| unanswerable | 8 | 50% |
| web | 20 | 30% |

## Failures

| Case | Scorer | Failed | Why (first failure) |
|---|---|---|---|
| `web-minimum-wage-start` | task_rubric | 1/1 | The answer gives only the year 1999 and says the sources lack the exact start date (1 April 1999) and the adult rate (GBP 3.60). It does not state either key point, though it does not contradict the key and it correctly declines to give a specific figure for the starting rate. |
| `web-minimum-wage-start` | quality | 1/1 | 2.3/5 (correct 2, helpful 2, clear 3): The answer fails to give the 1 April 1999 start date and the £3.60 adult rate that the reference provides, claiming the sources lack them. It is well organised but largely unhelpful, with some padding about later National Living Wage figures. |
| `web-boe-independence` | quality | 1/1 | 3.7/5 (correct 4, helpful 4, clear 3): The answer correctly identifies the May 1997 announcement and the Bank of England Act 1998 as the formalising law, matching the reference. However, it is padded with many citation-laden bullets and a long limitations section that hedges more than needed, and it does not state the Act directly as the answer to the 'when' question. |
| `web-climate-change-act` | quality | 1/1 | 3.3/5 (correct 4, helpful 4, clear 2): The core answer matches the reference (80% by 2050 vs 1990, amended to 100%/net zero in 2019), but the response is padded with citation tags, a confusing 'Limitations' section about tables of contents, and an odd claim about the original target year, which hurts clarity. |
| `web-brexit-dates` | quality | 1/1 | 3.7/5 (correct 4, helpful 4, clear 3): The core dates (31 January 2020 exit, 31 December 2020 transition end) match the reference and are answered up front, but the answer pads with background on extensions and adds unverified time-of-day details, and its limitations note about whether the transition was extended is confusing and somewhat contradicts its own claim that it ended on 31 December 2020. |
| `web-bletchley-declaration` | quality | 1/1 | 3.7/5 (correct 4, helpful 4, clear 3): The answer matches the reference on date, venue, 28 countries plus EU, and frontier AI safety focus, and adds useful context. However, it is padded with summit and aftermath details beyond what was asked, cites source tags and 'the notes' framing awkwardly, and its claim about developers submitting models for testing and the 29-governments figure are not in the reference, muddying clarity. |
| `web-gdpr-article-17` | trajectory_efficiency | 1/1 | fetch_url repeated 4x with the same arguments |
| `web-transformer-paper` | trajectory_efficiency | 1/1 | fetch_url repeated 3x with the same arguments |
| `web-equality-act` | trajectory_efficiency | 1/1 | fetch_url repeated 3x with the same arguments |
| `web-london-underground-opening` | task_rubric | 1/1 | The answer gives the 10 January 1863 opening date, though it does not explicitly tie that railway to the London Underground name. It says the first section ran between Paddington and King's Cross, which conflicts with the key's Paddington to Farringdon route and does not state Farringdon. |
| `web-london-underground-opening` | quality | 1/1 | 2.0/5 (correct 2, helpful 2, clear 2): The answer gives the correct date (10 January 1863) but says the first section ran between Paddington and King's Cross, contradicting the reference's Paddington to Farringdon, and it hedges heavily about the London Underground link. It also includes irrelevant source-processing commentary about Instagram and hidden text, which clutters the response. |
| `web-decimal-day` | quality | 1/1 | 3.7/5 (correct 5, helpful 3, clear 3): The core facts match the reference: Decimal Day on 15 February 1971, and the pound divided into 100 new pence instead of 240 old pence. However, it pads the answer with planning history, coin dates and meta-notes about sources, and the closing limitations section is confusing and partly self-contradictory. |
| `web-ben-nevis-height` | task_rubric | 1/1 | The answer states Ben Nevis is 1,345m, matching key point 1, but does not give the feet equivalent (4,413 ft) and does not mention it is the highest mountain in the UK, so key point 2 is missing. Nothing contradicts the key. |
| `web-ben-nevis-height` | quality | 1/1 | 3.7/5 (correct 4, helpful 4, clear 3): The core figure of 1,345m matches the reference and answers the question directly, but the answer pads heavily with survey history and cites a source tag the user never supplied, and it omits the feet conversion and the UK-highest fact the reference includes. |
| `web-penicillin-discovery` | task_rubric | 1/1 | The answer credits Alexander Fleming with the discovery in 1928 and says it took place in London, which covers points 1 and 2. It explicitly says the notes do not identify the building, so it does not state St Mary's Hospital and point 3 is not covered. Nothing it says conflicts with the key. |
| `web-human-rights-act` | quality | 1/1 | 3.3/5 (correct 4, helpful 4, clear 2): The answer gives the correct main commencement date (2 October 2000) and describes the Act's purpose accurately, but it is padded with staged-commencement detail and citation tags, and the limitations section (mentioning hidden instructions in a source) is irrelevant to the user's question and reads poorly. |
| `web-gold-standard-exit` | quality | 1/1 | 3.3/5 (correct 4, helpful 3, clear 3): The answer gives the right date (21 September 1931) and supporting detail, but it hedges that the sources give no further date and it is padded with background and citation markers, obscuring the direct answer that the UK suspended the gold standard on that date. |
| `docs-trip-approval` | quality | 1/1 | 3.7/5 (correct 4, helpful 4, clear 3): The core answer matches the reference (GBP 1,500 needs line manager and Finance; international needs a Director), but it adds hotel-cap and reimbursement details beyond the question and includes a muddled limitation claiming the policy doesn't say what applies to trips both international and over GBP 1,500, which is contradicted by its own bullets. |
| `docs-incident-root-cause` | trajectory_efficiency | 1/1 | web_search repeated 4x with the same arguments |
| `docs-ax7-battery` | quality | 1/1 | 3.7/5 (correct 4, helpful 4, clear 3): The answer correctly gives the 9-hour typical runtime and the 0-to-80-percent in 55 minutes at a Quillmere dock, matching the reference. However, it pads with source citations, extra battery specs and limitations, and it oddly calls the spec 'fictional' and mentions an evaluation set, which is confusing and off-topic for the user. |
| `docs-ax7-price` | quality | 1/1 | 3.7/5 (correct 4, helpful 4, clear 3): The answer gives the reference prices accurately (GBP 41,500 per robot and GBP 2,100 per robot per year) and answers the question directly, but it pads with source-citation sections and a limitations list that go beyond what was asked, and it never states an explicit combined figure for one robot with software.[S2] |
| `both-ax7-battery-voltage` | task_rubric | 1/1 | The answer correctly identifies LiFePO4 as the AX-7 chemistry (point 1) but says the single-cell nominal voltage is not available from the sources, so it does not state the ~3.2 V figure (point 2 not covered). It does not contradict the key, and it does not present a wrong cell voltage. |
| `both-ax7-battery-voltage` | quality | 1/1 | 2.3/5 (correct 2, helpful 2, clear 3): The answer correctly identifies LiFePO4 chemistry but fails to give the nominal cell voltage (about 3.2 V) that the reference expects, instead claiming it is unavailable. It is well organized, but the pack-level detail and source citations pad the response without answering the second part. |
| `both-iso-3691-4` | task_rubric | 1/1 | The answer key says the AX-7 is certified to ISO 3691-4, but the answer says the sources do not state the AX-7's certification and explicitly refuses to link ISO 3691-4 to the AX-7. It does correctly describe what ISO 3691-4 covers, matching key point 2, but it does not state key point 1 and does not contradict it. |
| `both-iso-3691-4` | quality | 1/1 | 2.3/5 (correct 2, helpful 2, clear 3): The answer says the AX-7's certification is not stated in its sources, but the reference says it is certified to ISO 3691-4, so the core claim contradicts the reference. It does give useful background on the standard, but it cites sources and an incident report that the question never provided, and it adds unrelated safety-feature details. |
| `both-mileage-vs-hmrc` | quality | 1/1 | 3.3/5 (correct 3, helpful 4, clear 3): The answer gives the right core conclusion (Quillmere's 45p is below HMRC's 55p from 6 April 2026, having matched earlier) and directly answers the question, but it cites source tags and contains a 'Source coverage' section and limitations that add clutter and an unexplained contradiction about S1/S2 that the reader cannot resolve. |
| `both-daventry-county` | task_rubric | 1/1 | The answer correctly identifies the Daventry fulfilment site as the outage location (key point 1), but it explicitly states that the county is not answered by the sources, so it fails to give Northamptonshire (key point 2). It does not contradict the key. |
| `both-daventry-county` | quality | 1/1 | 2.3/5 (correct 2, helpful 2, clear 3): The answer identifies Daventry correctly but fails to give the county (Northamptonshire), claiming the sources don't state it, which contradicts the reference; it is also padded with tangential Coventry details and somewhat repetitive bullets. |
| `both-ax7-ip-rating` | task_rubric | 1/1 | The answer states the AX-7 is rated IP54, matching key point 1. It explicitly says the notes do not explain what the digits 5 and 4 mean, so it omits the dust protection meaning of 5 and the splashing-water meaning of 4. It does not state anything that conflicts with the key. |
| `both-ax7-ip-rating` | quality | 1/1 | 2.0/5 (correct 2, helpful 2, clear 2): It correctly gives IP54 but never explains what the 5 (dust) or 4 (splashing water) mean, claiming the sources don't say, and it contradicts itself by saying the spec states no rating while also citing S3 for IP54. |
| `both-singapore-cabin-class` | task_rubric | 1/1 | The answer correctly states the policy rule that premium economy applies to flights over 6 hours and economy to 6 hours or less, which covers key point 1. It does not state that a direct London to Singapore flight takes about 13 hours or conclude that premium economy is allowed, instead saying the duration cannot be confirmed, so key point 2 is not covered. |
| `both-singapore-cabin-class` | quality | 1/1 | 2.3/5 (correct 2, helpful 2, clear 3): The answer refuses to conclude premium economy even though the reference gives a ~13-hour duration that clearly falls under the over-6-hours rule, so it misses the expected answer; it is well organised but over-hedged and padded with irrelevant policy details. |
| `both-leeds-population` | trajectory_efficiency | 1/1 | rag_search repeated 3x with the same arguments |
| `both-coventry-river` | task_rubric | 1/1 | The answer correctly states the AX-7 is assembled in Coventry, but it says the sources do not name the river through Coventry, so the River Sherbourne point is not covered. |
| `both-coventry-river` | quality | 1/1 | 2.3/5 (correct 2, helpful 2, clear 3): The answer correctly gives Coventry as the assembly city but wrongly says the sources do not name a river, missing the River Sherbourne from the reference; it also pads with irrelevant Leeds and Daventry details, though the structure is readable. |
| `none-january-2026-minutes` | quality | 1/1 | 3.7/5 (correct 5, helpful 4, clear 2): Correctly states the January 2026 decision is not reported and gives the October 2025 Leeds approval accurately, but the answer repeats the same bullet about the January meeting and includes a distracting note about hidden instructions in an unrelated source. |
| `none-ax7-ramp-payload` | quality | 1/1 | 3.3/5 (correct 4, helpful 3, clear 3): The answer correctly recognizes that the ramp payload cannot be determined from the sources, but it is repetitive (the same spec and speed points are stated twice) and pads with irrelevant source details rather than stating the limitation crisply. |
| `none-future-wimbledon` | quality | 1/1 | 3.3/5 (correct 5, helpful 3, clear 2): Correctly states the question cannot be answered from the sources, matching the reference, but pads the answer with irrelevant robot specification details and repeats the AX7 facts redundantly, which hurts clarity and directness. |
| `none-fictional-company-revenue` | hallucination | 1/1 | 1/4 claims unsupported: Threnwick Quantasys Ltd is a Norwich photonics firm. |
