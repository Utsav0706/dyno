# Connecting to Dyno

Dyno connects to the other projects only through HTTP, its CLI, its Python API and
plain files (YAML cases, JSONL failures). Nothing imports another repo's code.

## Agents Dyno can run

| Agent | How Dyno reaches it | Settings |
|---|---|---|
| `scout` | Scout's API: `POST /research`, poll `GET /research/{id}`, `GET /research/{id}/trajectory` | `SCOUT_URL`, `SCOUT_CORPUS_DIR` |
| `gearbox` | Gearbox's OpenAI-style `POST /v1/chat/completions` (`model: auto`); `x-gearbox-*` headers give model, cost and routing reason | `GEARBOX_URL` |
| anything else | a class with `run(input: str) -> AgentResult`, named as `package.module:Class` | |

## The gate, from Python (for Pitwall's `promote.py`)

```python
from dyno.gate import gate

result = gate("candidate_run_id", "baseline_run_id", max_drop=2.0)
if not result.passed:
    raise SystemExit(f"not promoted: {result.reason}")
```

`GateResult` fields: `passed`, `metric`, `baseline`, `candidate`, `drop_pp` (positive
means worse), `max_drop`, `compared_cases`, `newly_failing`, `reason`.

- `metric`: `attempt_pass_rate` (default), `pass_at_k`, `pass_hat_k`, or a scorer name
  such as `task_rubric`.
- `no_new_failures=True` also fails the gate when any case that passed now fails.
- Only the cases both runs share are compared; runs with no shared cases fail the gate.
- Pass `store=Store(open_engine(url))` to use a database other than `DATABASE_URL`.

The CLI does the same and exits 1 on a fail:

```bash
dyno gate CANDIDATE --baseline BASELINE --max-drop 2.0 --metric task_rubric
```

**Noise.** On 50 cases, 2 points is one case, and agents give different answers to the
same question. Gate on runs with `--k 3` so one unlucky attempt doesn't decide a release.

## Production failures -> new cases

A JSONL file, one failed production answer per line. Only `input` is required.

```json
{"id": "optional", "input": "the question", "output": "what the agent said", "expected": "optional answer, or a list of key points", "reason": "optional: why it was bad", "tags": ["optional"], "source": "optional, e.g. scout-feedback"}
```

```bash
dyno import-failures failures.jsonl --out runs/new_cases.yaml --existing suites/my_suite.yaml
dyno run suites/scout.yaml --cases runs/new_cases.yaml
```

- Case id: the given `id`, else `prod-` + the first 8 hex digits of the SHA-256 of the
  normalised input, so the same failure always becomes the same case.
- Repeats (within the file, or already in an `--existing` suite) are skipped.
- Tags: `production`, the line's `tags`, and its `source`.
- `output` and `reason` are written as comments above each case, for whoever adds the
  answer key; they aren't case fields.
- Without `expected`, the `quality` and `hallucination` judges still apply; `task_rubric`
  needs an answer key.

## Results as files

- `dyno report RUN --format json`: one run.
- `dyno compare A B --format json`: two runs.
- `dyno cluster RUN... --format json`: failure clusters.
- Every CI eval run uploads its `dyno.db`; `dyno import path/to/dyno.db` merges it into a
  local database.
