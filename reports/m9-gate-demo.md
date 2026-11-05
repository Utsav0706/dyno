# The CI gate blocking a bad pull request

**The change** ([Utsav0706/scout#2](https://github.com/Utsav0706/scout/pull/2), made
bad on purpose and not merged): a cost cut in Scout's `config.yaml`. Scout reads 2
sources per question instead of 8, and sends 1,500 characters of each to the reader
and verifier instead of 8,000.

**Scout's unit tests pass** (CI run 42059065583). They use scripted models, so they
can't tell a good answer from a bad one. A configuration or prompt change is invisible
to them.

**The Dyno gate fails it** (`dyno-gate` workflow, run 42059429740, started by the
`eval` label). It ran the 5 `ci` golden cases on Scout `main` (`3d79c87`) and on the
pull request (`b676e17`), one after the other in the same job. Both runs used the
cases from `main` and the same calibrated judges.

```
FAIL: task_rubric dropped 40.0 pts (80% -> 40%), more than 20.0
newly failing: docs-london-hotel-cap, web-brexit-dates
```

| | main | pull request | Change |
|---|---|---|---|
| Task success (task_rubric) | 4/5 | **2/5** | -40 pts |
| Every scorer passed | 4/5 | 1/5 | -60 pts |
| Quality (correct and helpful >= 4) | 4/5 | 3/5 | |
| Hallucination check passed | 5/5 | 5/5 | |
| Cost per question | GBP 0.0198 | **GBP 0.0249** | **+26%** |
| Median time per question | 28 s | 40 s | +43% |

| Case | main | pull request |
|---|---|---|
| web-brexit-dates | pass | **fail**: says the transition period was "due to expire" on 31 December 2020 and won't confirm it ended then |
| docs-london-hotel-cap | pass | **fail**: "the available claims do not state a specific maximum hotel rate for London" (it is GBP 190) |
| both-ax7-battery-voltage | pass | pass (task); failed the loop check |
| none-quillmere-2021-revenue | pass | pass |
| web-minimum-wage-start | fail | fail (fails on `main` too, see M8) |

## The cost cut cost more

The change was meant to save money, but cost per question went up 26%. Model calls by
Scout node, all 5 questions:

| Node (model) | main: calls, GBP | pull request: calls, GBP |
|---|---|---|
| reader (Haiku) | 21, 0.0031 | 19, 0.0024 |
| writer (Sonnet) | 6, 0.0447 | 8, 0.0560 |
| reviser (Sonnet) | 2, 0.0076 | 4, 0.0167 |
| researcher (Haiku) | 49, 0.0203 | 55, 0.0246 |

Reading was 3% of the spend, so cutting it saved GBP 0.0007. The thinner notes left
more gaps, which sent more questions into Scout's second research round, so the
expensive Sonnet writer and reviser ran more often. Without the eval, the change would
have looked like a saving: fewer reader calls and unchanged unit tests.

## What the demo found in Dyno

When gating on one scorer (`--metric task_rubric`), the gate's "newly failing" list,
and its `--no-new-failures` rule, still judged cases by every scorer. The first summary
listed `both-ax7-battery-voltage` as newly failing, although it answered correctly and
only tripped the loop check. Fixed: with a scorer metric, cases are judged by that
scorer alone (`dyno compare --scorer`). The verdict didn't change; the list above uses
the fixed version, re-run on the downloaded database. The M8 gate (`task_rubric`,
`--no-new-failures`) passed under the old rule, which was the stricter of the two, so
that result still holds.

## Caveats

- 5 cases, 1 attempt each: enough to catch a change this bad, not a subtle one. The
  20-point allowance tolerates one case flipping by chance. Decisions about real
  changes should be made on k = 3 runs ([docs/ci-gate.md](../docs/ci-gate.md)).
- The two runs ran minutes apart against the live web; different search results can
  move a case either way.

Spend: Scout GBP 0.22 (0.099 + 0.124), judges GBP 0.025; 57 Tavily searches.
