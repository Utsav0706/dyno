# Gating pull requests with Dyno

`action.yml` at the root of this repo is a GitHub Action that fails a pull request's
check when the agent scores worse than the base branch on the same cases.

## How it works

One job, two runs, the same day:

1. Start the agent from the **base** branch, then `uses: Utsav0706/dyno@main` with
   `role: baseline`. Dyno runs the cases and remembers the run id.
2. Stop it and start the agent from the **pull request's** code, then use the action
   again with `role: candidate`. Dyno runs the same cases, compares the two runs, writes
   the comparison to the job summary and fails the step if `dyno gate` fails.

Why both runs every time, rather than comparing with a stored baseline: an agent that
searches the web gets different pages from week to week, so last month's baseline
isn't a fair comparison. It doubles the cost of each gate.

Starting and stopping the agent stays in your workflow, because only your repo knows
how. The action needs Python 3 on the runner and installs Dyno in its own virtualenv.

## Inputs

| Input | Default | |
|---|---|---|
| `role` | (required) | `baseline` or `candidate` |
| `suite` | (required) | suite YAML: agent, k, scorers (and cases unless `cases` is set) |
| `cases` | | take the cases from this file instead; use the **base** branch's copy for both runs, so a pull request can't change its own test |
| `run-args` | | extra `dyno run` options, e.g. `--k 3 --tags ci`; the same for both roles |
| `metric` | `attempt_pass_rate` | or `pass_at_k`, `pass_hat_k`, a scorer name such as `task_rubric` |
| `max-drop` | `2.0` | largest allowed drop, in percentage points |
| `no-new-failures` | `false` | also fail if any case that passed on the base now fails |
| `baseline-run` | | candidate only: compare with this run id instead |
| `database` | `dyno-gate.db` | the SQLite file both roles share; upload it as an artifact to look into a failure (`dyno import`, `dyno dashboard`) |

Outputs: `run-id`, and for the candidate `passed` (`true` / `false`). Agent settings
and keys (for example `SCOUT_URL`, `ANTHROPIC_API_KEY` for the judge scorers) go in the
step's `env`.

## Example: Scout

Scout's [`.github/workflows/dyno-gate.yml`](https://github.com/Utsav0706/scout/blob/main/.github/workflows/dyno-gate.yml)
runs when a pull request gets the label `eval`, so ordinary pull requests cost nothing:

```yaml
- uses: Utsav0706/dyno@main
  env:
    SCOUT_CORPUS_DIR: ${{ github.workspace }}/eval-setup/corpus
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  with:
    role: baseline
    suite: dyno/suites/scout.yaml
    cases: base/eval/golden.yaml
    run-args: --tags ci

# ... stop Scout, start it from the pull request's code ...

- uses: Utsav0706/dyno@main
  env: {...}
  with:
    role: candidate
    suite: dyno/suites/scout.yaml
    cases: base/eval/golden.yaml
    run-args: --tags ci
    metric: task_rubric
    max-drop: "20"
```

## Choosing the threshold

Agents are random. The same Scout code scored 70% on 10 questions in one run and 47%
over three attempts each in another, so a 2-point threshold on a small run blocks
harmless changes.

- For a real release decision: `--k 3` and enough cases that one case is a small step
  (on 50 cases x 3, one attempt is 0.7 points).
- For a cheap check on every labelled pull request: few cases, k = 1, a metric that the
  calibrated judges measure well (`task_rubric`), and a threshold that tolerates one case
  flipping (on 5 cases, one case is 20 points). That catches a broken change, not a
  subtle one.

## Cost and safety

- Each gate runs the cases twice. For Scout's 5 `ci` cases at k = 1: about GBP 0.25 of
  agent spend plus GBP 0.03 of judges.
- Run it on a label or by hand, not on every push.
- GitHub doesn't pass secrets to pull requests from forks, so the gate only runs for
  branches in the repo itself. Don't switch it to `pull_request_target` to get around
  that: the agent runs the pull request's code with your keys.
