# FAQ

## What is Dyno?

A tool that tests AI agents. It runs an agent on a set of questions (cases), several
times each, records every model and tool call it makes, scores each attempt, and tells
you how good the agent is, how reliably it gets each question right, and whether a
change made it worse. Its name comes from the dynamometer: the rig a car's engine is
measured on.

## Can I try it without an API key?

Yes. The built-in example agent is deterministic and free:

```powershell
.venv\Scripts\dyno.exe run examples\example_suite.yaml --agent example --k 3
.venv\Scripts\dyno.exe report <run_id>
```

Three of its six cases are meant to fail, so the report has something to show. The LLM
judges need `ANTHROPIC_API_KEY` in `.env`, and only run when a suite lists them.

## Why not just use promptfoo, Inspect or DeepEval?

For most work, do. [comparison.md](comparison.md) goes through what each one does.
Dyno differs in a few choices: it checks its judges against human labels with Cohen's
kappa, its CI gate compares a pull request with its base branch run the same day, and
it drives agents over HTTP exactly as a user would.

## How do you know the LLM judges are right?

By measuring them. 40 Scout answers and 30 single claims were labelled by hand, blind to
the judges' verdicts, and `dyno calibrate` computed Cohen's kappa (agreement corrected
for chance; 0.6 or more is the usual bar for "substantial"):

| Judge | kappa |
|---|---|
| task_rubric (are the expected key points in the answer?) | 1.00 |
| quality v2 | 0.95, measured on the labels it was tuned on, so optimistic |
| hallucination (is each claim supported by what the agent read?) | 0.63 |

The hallucination judge is the weakest. Fresh labels on a later run are the real test
for all three.

## Why did the first quality judge fail?

It marked down good answers for their formatting: citation tags like `[S3]` and long
"Limitations" sections. The labeller passed 7 answers it failed, all for format.
Version 2 stops scoring format, caps "correct" at 3 when a key point is missing, and
passes on correctness and helpfulness. Kappa went from 0.56 to 0.95.

## What is the difference between pass@k and pass^k?

Run each case k times. **pass@k**: the share of cases answered correctly at least once.
**pass^k**: the share answered correctly every time. A user gets one attempt, so pass^k
is closer to what they see. On 10 hard Scout questions at k = 3, pass@3 was 60% but
pass^3 40%: two questions Scout could answer, it didn't answer reliably.

## Why do the numbers change between runs of the same code?

Agents are random, and Scout searches the live web, which changes. The same Scout code
scored 70% on 10 questions in one run (one attempt each) and 47% in another (three
attempts each). That's why decisions use k = 3 and the gate compares runs made minutes
apart.

## Did Dyno actually improve anything?

Yes. `dyno cluster` showed that most of Scout's failures were reports that stopped at
"the sources don't give X" instead of searching for X. Scout's writer now names up to
two follow-up questions, which join Scout's existing retry round. On the same 10 hard
cases, 3 attempts each, task success went from 47% to 80% and no case got worse, at 30%
more cost per question ([reports/m8-before-after.md](../reports/m8-before-after.md)).
The fix was designed from those cases, so the fair test is the other 40 golden cases:
a full run is planned.

## What does the CI gate catch?

A Scout pull request that looked like a cost cut (read 2 sources instead of 8) passed
every Scout unit test, because those use scripted models. The gate ran 5 cases on
`main` and on the pull request: task success fell from 80% to 40%, so the check failed.
The change also cost 26% more per question, not less
([reports/m9-gate-demo.md](../reports/m9-gate-demo.md)).

## What does it cost?

Dyno itself is free. Judges cost under GBP 0.001 a call, about GBP 0.0025 for all three
on one Scout answer, and stop at `JUDGE_BUDGET_GBP` (default GBP 1) per command. The
agent's own cost is the agent's: a Scout question costs about GBP 0.02-0.03. A gate run
on 5 Scout cases (base plus pull request) costs about GBP 0.25. Building Dyno, with every
evaluation run in this repo, has cost under GBP 4 of API spend so far.

## Can I test my own agent?

Yes. Write a class with `run(self, input: str) -> AgentResult`, then
`dyno run my_suite.yaml --agent mypackage.agents:MyAgent`. If your agent is a web
service, an adapter like `src/dyno/agents/gearbox.py` (80 lines) is the pattern.
The case format is at the top of `src/dyno/cases.py`.

## Can it gate my repository's pull requests?

Yes, with `uses: Utsav0706/dyno@main` twice in a job: once after starting your agent
from the base branch, once after starting it from the pull request.
[ci-gate.md](ci-gate.md) has the inputs, an example and advice on thresholds. Run it on
a label or by hand: each gate runs your agent twice.

## Where are the results stored?

In one SQLite file, `dyno.db` by default (`DATABASE_URL` takes any SQLAlchemy URL). Every
attempt, step, score and label is there. `dyno dashboard` opens a local read-only view of
it, and `dyno import` copies runs in from another file, such as a CI run's artifact.

## What doesn't it do?

No sandboxes for running agent code, no red teaming, judges only through Anthropic, a
sequential runner (fine for 50 cases x 3, slow for thousands), and no hosted sharing.
