# Dyno

[![CI](https://github.com/Utsav0706/dyno/actions/workflows/ci.yml/badge.svg)](https://github.com/Utsav0706/dyno/actions/workflows/ci.yml)

An evaluation harness for AI agents. Dyno runs an agent on a set of test cases, records
every step it takes (model calls, tool calls, results), scores the run, compares it with
earlier runs, and fails CI when quality drops.

Not just "was the final answer right?" but: did it use the right tools, in a sensible
number of steps, without making things up, at what cost, and does it pass every time
or only sometimes?

Status: **M1, runner and store**: YAML cases, the `Agent` protocol, `dyno run` with k
repeats, and every attempt and step stored in SQLite. Scorers come next. One of four connected
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
automatically.

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
