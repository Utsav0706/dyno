# Dyno

[![CI](https://github.com/Utsav0706/dyno/actions/workflows/ci.yml/badge.svg)](https://github.com/Utsav0706/dyno/actions/workflows/ci.yml)

An evaluation harness for AI agents. Dyno runs an agent on a set of test cases, records
every step it takes (model calls, tool calls, results), scores the run, compares it with
earlier runs, and fails CI when quality drops.

Not just "was the final answer right?" but: did it use the right tools, in a sensible
number of steps, without making things up, at what cost, and does it pass every time
or only sometimes?

Status: **M0, skeleton** (CLI, config, logging, tests, CI). One of four connected
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
