# Baseline, 2026-11-02

First full Dyno runs, before any fix. Scout at `main` (`8cf8997`), Gearbox at `890e275`,
Dyno at `65186d3`. Judges: Claude Haiku 5.5, prompts `judge_task_v1`,
`judge_hallucination_v2`, `judge_quality_v2`. All three judges are calibrated against
hand labels (see [Calibration](#calibration) below).

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
| Quality (correct and helpful >= 4) | 90% | 100% | 30% | 100% | 82% |

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
3. **Quality was marked down mostly for format** (citation tags, long "Limitations"
   sections) by the first quality judge. Hand labels disagreed, so the judge was
   changed (below); with v2, quality fails track missing or wrong content.

## Gearbox

72% of prompts passed (task_rubric on the 94 with a gold answer: 67%; quality v2: 77%).
Two caveats from reading the failures: for coding prompts (HumanEval, MBPP) the "gold"
answer is reference code, and the task judge sometimes finds no key point in it and fails
a working solution, so task_rubric undercounts code (next Gearbox run: judge code on
quality only); and 5 hard prompts (AIME, MMLU-Pro) came back with an empty answer, likely
thinking using up Gearbox's 3,000-token cap, which is a Gearbox finding.
Routing: **117 of 119 prompts went to tier M (Haiku), 2 to L, none to S.** The embedding
router's probabilities sit near a third each (e.g. P(S) 0.37, P(M) 0.36, P(L) 0.27)
against a 0.6 threshold, so it falls back to M almost every time. Gearbox's own report
measured routing differently; this is a finding for the Gearbox repo, not fixed here.

## Calibration

Uv hand-labelled 40 Scout answers (task success, quality) and 30 single claims
(supported by the evidence or not), blind to the judges' verdicts. Sample: every item
the judge failed plus a random share of the rest. Full report, with every
disagreement: [../calibration.md](../calibration.md).

| Judge | Labels | Agreement | Cohen's kappa |
|---|---|---|---|
| task_rubric (`judge_task_v1`) | 40 | 100% | 1.00 |
| hallucination (`judge_hallucination_v2`) | 25 (+5 unsure) | 92% | 0.63 |
| quality, first version (`judge_quality_v1`, pass on mean of 3 scores >= 4) | 40 | 80% | 0.56 |
| quality (`judge_quality_v2`, pass on correct and helpful >= 4) | 40 | 98% | 0.95 |

The first quality judge failed 7 answers the labeller passed, each for format (citation
tags, limitations sections, extra context), and passed one that missed a key point. v2
stops penalising format, caps "correct" at 3 when a key point is missing, and passes on
correctness and helpfulness (clarity is still reported). **Caveat:** v2 was written
after reading these disagreements and is measured on the same 40 labels, so 0.95 is an
optimistic figure; fresh labels on a later run are the real test. With v2, quality
mostly agrees with task success; it still differs on clarity and on unanswerable
questions. All judges stay on Haiku 5.5 (every kappa >= 0.6, so Sonnet wasn't needed).
Re-judging quality on the 80 attempts cost GBP 0.013.
