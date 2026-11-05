# Fixing Scout's biggest failure cluster: before / after

**Change** (Scout branch `followup-research`, draft PR Utsav0706/scout#1, commit
`73ef557`): the writer now lists up to 2 follow-up questions for what its draft couldn't
answer, written with facts already found ("Which river flows through Coventry?"), and
those join Scout's existing single retry round. Before, that round only ran for
sub-questions with no sources or with every claim failing verification, so a partly
answered question never got a second search.

**Why this change:** `dyno cluster` on the baseline put most failures in clusters where
the report stops at "the sources don't give X" ([clusters-all.md](clusters-all.md)).

**Measurement:** the same 10 golden cases, 3 attempts each, before and after. Same eval
config, same calibrated judges (`judge_task_v1`, `judge_hallucination_v2`,
`judge_quality_v2` on Claude Haiku 5.5). 6 cases come from the target clusters; 4 already
passed (controls).

| | Before (Scout `main` 8cf8997) | After (`followup-research`) | Change |
|---|---|---|---|
| Task success (attempts) | 47% | **80%** | +33 pts |
| Cases right at least once in 3 (pass@3) | 6/10 | **9/10** | +3 |
| Cases right all 3 times (pass^3) | 4/10 | **7/10** | +3 |
| Hallucination check passed | 97% | 100% | +3 pts |
| Quality (correct and helpful >= 4) | 43% | 77% | +33 pts |
| Right tools | 100% | 100% | 0 |
| Failed attempts (any scorer) | 19 | 10 | -9 |
| Cost per question | GBP 0.0247 | GBP 0.0322 | **+30%** |
| Median time per question | 28 s | 46 s | **+64%** |
| Attempts with a second research round | 8/30 | 20/30 | |
| Web searches (Tavily) | 157 | 199 | +27% |

Task success per case (attempts passed out of 3):

| Case | Cluster | Before | After |
|---|---|---|---|
| both-ax7-battery-voltage | omits the second detail | 0 | **3** |
| both-daventry-county | omits the second detail | 0 | **3** |
| web-brexit-dates | says sources lack it | 1 | **3** |
| docs-london-hotel-cap | says sources lack it | 1 | 2 |
| both-company-size | won't draw the conclusion | 0 | 1 |
| web-minimum-wage-start | says sources lack it | 0 | 0 |
| web-boe-independence | control | 3 | 3 |
| web-speed-of-light | control | 3 | 3 |
| both-mileage-vs-hmrc | control | 3 | 3 |
| none-quillmere-2021-revenue | control (unanswerable) | 3 | 3 |

`dyno gate` (task_rubric, `--no-new-failures`): **PASS**. No case that passed before fails
now.

## What it didn't fix

- **Minimum wage (0/3).** In 2 of 3 attempts there was no second round: either the
  draft named no follow-up or the GBP 0.10 retry budget was already spent. The 1999
  GBP 3.60 rate is hard to find on today's web.
- **Loops** (same tool, same arguments, 3+ times) weren't targeted and still occur:
  3 of the 10 remaining failed attempts ([m8-clusters-after.md](m8-clusters-after.md)).
- **"Won't draw the conclusion"** (company size) only moved from 0/3 to 1/3.

## Caveats

- 10 cases, 30 attempts per side: a 33-point gain is far above the run-to-run noise
  seen on these cases, but it is one measurement.
- The fix was designed after reading failures from these same cases. The other 40
  golden cases are the fair test; they need the full 50-case run (about GBP 1.60 and
  300 Tavily searches), planned after the monthly Tavily reset.
- The gain costs more: +30% per question and +18 s median, mostly the extra research
  round now running on 2 of 3 questions instead of 1 in 4.

Reports: [m8-after-report.md](m8-after-report.md) (after run `e7749253d38c`),
[baseline/scout-subset-k3.md](baseline/scout-subset-k3.md) (before run `12fbcb8b0759`).
Spend: Scout GBP 0.97, judges GBP 0.10.
