# Dyno

[![CI](https://github.com/Utsav0706/dyno/actions/workflows/ci.yml/badge.svg)](https://github.com/Utsav0706/dyno/actions/workflows/ci.yml)

An evaluation harness for AI agents. Dyno runs an agent on a set of test cases, records
every step it takes (model calls, tool calls, results), scores the run, compares it with
earlier runs, and fails CI when quality drops.

Not just "was the final answer right?" but: did it use the right tools, in a sensible
number of steps, without making things up, at what cost, and does it pass every time
or only sometimes?

Status: **M2, deterministic scorers and reports**: YAML cases, the `Agent` protocol,
`dyno run` with k repeats, every attempt and step stored in SQLite, four deterministic
scorers, pass@k / pass^k, and `dyno report`. Next: HTTP adapters for Scout and Gearbox.
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

An attempt passes when every scorer that applied passed. Across the k attempts of a case,
the report gives **pass@k** (at least one passed), **pass^k** (all passed) and the
**flaky** cases (some passed, some failed). Choose scorers per suite:

```yaml
scorers:
  - task_success: {mode: exact}
  - tool_correctness
  - cost_latency: {max_cost_gbp: 0.05}
```

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
[examples/example_suite.yaml](examples/example_suite.yaml).
