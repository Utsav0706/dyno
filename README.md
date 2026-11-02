# Dyno

[![CI](https://github.com/Utsav0706/dyno/actions/workflows/ci.yml/badge.svg)](https://github.com/Utsav0706/dyno/actions/workflows/ci.yml)

An evaluation harness for AI agents. Dyno runs an agent on a set of test cases, records
every step it takes (model calls, tool calls, results), scores the run, compares it with
earlier runs, and fails CI when quality drops.

Not just "was the final answer right?" but: did it use the right tools, in a sensible
number of steps, without making things up, at what cost, and does it pass every time
or only sometimes?

Status: **M4, judge scorers**: YAML cases, the `Agent` protocol, `dyno run` with k
repeats, every attempt and step stored in SQLite, four deterministic scorers, three LLM
judge scorers, pass@k / pass^k, `dyno report`, HTTP adapters for Scout and Gearbox, and
a GitHub Actions eval for Scout's document cases. Next: the Scout baseline, then judge
calibration against hand labels.
One of four connected
projects: [Scout](https://github.com/Utsav0706/scout) (research agent),
[Gearbox](https://github.com/Utsav0706/gearbox) (LLM router), Dyno (eval harness) and
Pitwall (LLMOps).

## Run it locally (Windows PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\dyno.exe --help
.venv\Scripts\python.exe -m pytest
```

On Linux/CI the same steps are `make install` and `make check`.

## Try it (free, no API key)

```powershell
.venv\Scripts\dyno.exe run examples\example_suite.yaml --agent example --k 3
```

This runs the built-in example agent (deterministic, with a calculator and a lookup tool)
on 6 cases, 3 times each. Each attempt and its steps go into `dyno.db` (set
`DATABASE_URL` to change that). The database schema is created and upgraded
automatically. It prints a run id; then:

```powershell
.venv\Scripts\dyno.exe report <run_id>               # Markdown; --format json, --out FILE
.venv\Scripts\dyno.exe score <run_id>                # re-score a stored run, agent not called
```

## Scorers

Each scorer returns a score (0 to 1), pass/fail, and a one-line reason. "Not
applicable" (for example, no `max_steps` on the case) never counts as a pass or a fail.

| Scorer | Checks |
|---|---|
| `task_success` | answer vs `expected`: `contains` (default), `exact` or `regex`; key-point lists score the share found; `check: module:function` for your own check |
| `tool_correctness` | every `must_call` tool was called and no `must_not_call` tool was |
| `trajectory_efficiency` | steps (model and tool calls) within `max_steps`; no tool called 3+ times with the same arguments |
| `cost_latency` | cost (GBP), time and tokens; pass/fail only with `max_cost_gbp` / `max_latency_s` |
| `task_rubric` (judge) | every expected key point covered, in any wording, and none contradicted; for an `unanswerable` case, says the evidence isn't there without inventing an answer |
| `hallucination` (judge) | share of the answer's factual claims that the evidence the agent received (its tool results, plus the case's `sources`) doesn't support; passes at <= 10% |
| `quality` (judge) | correct, helpful and clear, 1-5 each; passes on a mean >= 4 |

Judge scorers call Claude Haiku 5.5 (`ANTHROPIC_API_KEY` in `.env`), cost a fraction of a
penny per attempt, and stop at `JUDGE_BUDGET_GBP` (default GBP 1 per command). Their
prompts are versioned files in [src/dyno/prompts/](src/dyno/prompts/), and every judged
score stores the prompt version, model, tokens, cost and the judge's full verdict. The
pass rules are in code, not in the prompts. If a judge call fails, that score counts as
a scorer error, never as an agent failure. Judges only run when a suite lists them.

An attempt passes when every scorer that applied passed. Across the k attempts of a case,
the report gives **pass@k** (at least one passed), **pass^k** (all passed) and the
**flaky** cases (some passed, some failed). Choose scorers per suite:

```yaml
scorers:
  - task_success: {mode: exact}
  - tool_correctness
  - cost_latency: {max_cost_gbp: 0.05}
```

Add scorers to a run you already have, without calling the agent again:
`dyno score <run_id> --suite suites/scout.yaml`.

## Checking the judges against a human

A judge's numbers are only worth something if it agrees with a person. Dyno measures that:

```powershell
.venv\Scripts\dyno.exe import runs\ci-123\dyno.db      # bring a CI run's database in
.venv\Scripts\dyno.exe label task                      # you mark answers pass/fail, blind
.venv\Scripts\dyno.exe label claims                    # and single claims supported or not
.venv\Scripts\dyno.exe calibrate --out reports\calibration.md
```

`label` never shows the judge's verdict, saves each label as you go (quit with `q`,
carry on later), and samples every item the judge failed plus a random share of the
rest. `calibrate` reports Cohen's kappa per judge (agreement corrected for chance; 0.6
or more counts as trusted) and lists every disagreement with the judge's reason.

## Plug in an agent

An agent is anything with a `run(input: str) -> AgentResult` method. It doesn't need to
inherit from anything:

```python
from dyno.agent import AgentResult, Step


class MyAgent:
    def run(self, input: str) -> AgentResult:
        return AgentResult(
            final_answer="...",
            steps=[Step(type="tool_call", name="web_search", args={"q": input})],
        )
```

Run it with `dyno run suite.yaml --agent mypackage.agents:MyAgent`. The case format is
documented at the top of [src/dyno/cases.py](src/dyno/cases.py), and an example is in
[examples/example_suite.yaml](examples/example_suite.yaml). Run part of a suite with
`--tags web --tags docs` or `--ids case-1 --ids case-2`.

## Built-in adapters

| Agent | Talks to | Each attempt |
|---|---|---|
| `scout` | Scout's API (`SCOUT_URL`, default `http://127.0.0.1:8001`) | signs up a fresh user per run, uploads PDFs from `SCOUT_CORPUS_DIR` if set, starts a research job, waits for it, then reads its trajectory (every model and tool call) |
| `gearbox` | Gearbox's OpenAI-style API (`GEARBOX_URL`, default `http://127.0.0.1:8002`) | one chat completion with `model: auto`; the chosen model, cost and routing reason come from Gearbox's headers |

Scout's golden set is already in Dyno's format:

```powershell
.venv\Scripts\dyno.exe run "..\scout\eval\golden.yaml" --agent scout --tags web
.venv\Scripts\dyno.exe run examples\gearbox_smoke.yaml
```
