# Baseline, 2026-11-02

First full Dyno runs, before any fix. Scout at `main` (`8cf8997`), Gearbox at `890e275`,
Dyno at `65186d3`. Judges: Claude Haiku 5.5, prompts `judge_task_v1`,
`judge_hallucination_v2`, `judge_quality_v1`. **Not yet calibrated against hand labels**
(that's next), so treat judged numbers as provisional.

| Run | Report | Attempts | Agent cost | Judge cost |
|---|---|---|---|---|
| Scout, golden set, 50 x 1 | [scout-50.md](scout-50.md) | 50 | GBP 1.24 | GBP 0.15 |
| Scout, 10-case subset, k = 3 | [scout-subset-k3.md](scout-subset-k3.md) | 30 | GBP 0.74 | GBP 0.09 |
| Gearbox, 119 held-out prompts | [gearbox-test.md](gearbox-test.md) | 119 | GBP 0.04 | GBP 0.04 |

## Scout: task success (task_rubric) by category, 50 x 1

| | web | docs | both | unanswerable | all |
|---|---|---|---|---|---|
| Cases | 20 | 12 | 10 | 8 | 50 |
| Task success | 80% | 100% | 40% | 100% | 80% |
| Hallucination check passed | 100% | 100% | 100% | 88% | 98% |
| Quality >= 4 | 50% | 75% | 30% | 63% | 54% |

Tools were always right (100%). 5 runs repeated a call with the same arguments 3+ times
(mostly `fetch_url`). Median 30 s, GBP 0.025 per question.

## Scout: reliability, 10 cases x 3 (task_rubric only)

| Case | Passed | |
|---|---|---|
| web-boe-independence, web-speed-of-light, both-mileage-vs-hmrc, none-quillmere-2021-revenue | 3/3 | reliable |
| web-brexit-dates, docs-london-hotel-cap | 1/3 | **flaky** |
| web-minimum-wage-start, both-ax7-battery-voltage, both-daventry-county, both-company-size | 0/3 | consistent failure |

pass@3 60%, pass^3 40% on task success: 2 of the 6 cases that can pass don't pass
reliably.

## What the failures have in common (first read; clustering comes later)

1. **The second hop never happens** (6 of the 10 task failures, all in `both`): Scout
   finds the fact in the documents ("assembled in Coventry") but then says the sources
   don't give the web half ("the river through Coventry") instead of searching for it.
2. **A false "not found"**: the answer says a fact is missing although Scout retrieved
   it. In one hotel-cap attempt the answer says there's no London cap while its own
   limitations section mentions GBP 190. Seen in the flaky docs and web cases.
3. **Quality is marked down mostly for format**: citation tags, long "Limitations"
   sections and notes about the search, rather than wrong content. Calibration will
   show whether the quality judge agrees with a human here.

## Gearbox

72% of prompts passed (task_rubric on the 94 with a gold answer: 67%; quality: 80%).
Routing: **117 of 119 prompts went to tier M (Haiku), 2 to L, none to S.** The embedding
router's probabilities sit near a third each (e.g. P(S) 0.37, P(M) 0.36, P(L) 0.27)
against a 0.6 threshold, so it falls back to M almost every time. Gearbox's own report
measured routing differently; this is a finding for the Gearbox repo, not fixed here.
