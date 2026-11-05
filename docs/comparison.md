# Dyno next to Inspect, promptfoo and DeepEval

Short answer: for real work, use one of these. They are maintained by teams, used
widely, and do far more than Dyno: sandboxes, red teaming, hosted dashboards, dozens
of metrics, many model providers. Dyno is a small harness built to evaluate two
specific agents (Scout and Gearbox) end to end, and to learn what that takes. This
page says where they overlap and the few places Dyno takes a different approach.

Checked against each project's documentation in November 2026. If something here is
out of date, their docs win.

## What each one is

- **[Inspect](https://inspect.aisi.org.uk/)** (UK AI Security Institute): Python
  framework of tasks, datasets, solvers and scorers. Built-in ReAct agent, an Agent
  Bridge for outside agents, tools, sandboxes (Docker, Kubernetes and more), model
  grading, a log viewer, and epochs with reducers including `pass_at_{k}` and
  `pass_k_{k}` ([metrics](https://inspect.aisi.org.uk/metrics.html)).
- **[promptfoo](https://www.promptfoo.dev/docs/intro/)**: YAML-configured CLI and Node
  library for testing prompts, models and agents. Deterministic and model-graded
  assertions, including trajectory assertions (`trajectory:tool-used`,
  `trajectory:tool-sequence`, `trajectory:step-count`, `trajectory:goal-success`)
  ([assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/)),
  `--repeat`, a web viewer, red teaming, and a
  [GitHub Action](https://www.promptfoo.dev/docs/integrations/github-action/). CI
  fails below `PROMPTFOO_PASS_RATE_THRESHOLD`.
- **[DeepEval](https://deepeval.com/docs/getting-started)**: pytest-style test cases
  run with `deepeval test run`. Metrics such as G-Eval and
  [tool correctness](https://deepeval.com/docs/metrics-tool-correctness), tracing of
  agent components with `@observe`, trajectory and component-level evaluation, and the
  hosted Confident AI platform for viewing and comparing runs.

## Side by side

| | Inspect | promptfoo | DeepEval | Dyno |
|---|---|---|---|---|
| Cases as data files | Python + datasets | YAML | Python / datasets | YAML |
| Agent's tool calls checked | yes | yes (`trajectory:*`) | yes (tool correctness, traces) | yes (`tool_correctness`, `trajectory_efficiency`) |
| Repeats per case | epochs | `--repeat` | | `--k` |
| pass@k and pass^k | yes (reducers) | | | yes, plus a list of flaky cases |
| LLM judges | yes | yes (`llm-rubric`, `g-eval`, ...) | yes (G-Eval and more) | three, Claude Haiku 5.5 |
| Viewer | Inspect View | web viewer | Confident AI (hosted), `deepeval inspect` | `dyno dashboard` (local) |
| CI | | GitHub Action, pass-rate threshold | `deepeval test run` | GitHub Action, gate vs the base branch |
| Sandboxes, red teaming, many providers | sandboxes | red teaming, many providers | | no |

A blank cell means I didn't find it in the docs I read, not that it's missing.

## Where Dyno takes a different approach

These are choices, not features the others lack the ability to build. Several can be
done in the other tools with some code.

1. **Measuring the judge against a person, built in.** `dyno label` shows answers
   blind to the judge's verdict, and `dyno calibrate` reports Cohen's kappa per judge
   with every disagreement. That is how Dyno found its first quality judge marking
   down good answers for their formatting (kappa 0.56) and replaced it (0.95). I
   didn't find a built-in step for this in the three tools' docs; their judges are
   configurable, but checking one against your own labels is left to you.
2. **The gate compares a pull request with its base, run the same day.** promptfoo's
   CI check is an absolute pass-rate threshold; Dyno's is "no worse than `main`, on
   the same cases, minutes apart". For an agent that searches the live web, a fixed
   threshold or an old baseline drifts as the web changes.
3. **Agents are black boxes over HTTP.** The Scout adapter drives Scout's public API
   and reads its trajectory endpoint, so Dyno evaluates exactly what a user gets, in
   any language, without importing the agent. Inspect's Agent Bridge and DeepEval's
   tracing go the other way: deeper hooks into the agent's code.
4. **Failure clustering.** `dyno cluster` groups failed attempts by their scorers'
   explanations (local embeddings, k-means) and names each group, which is how M8
   picked what to fix in Scout.
5. **Every judged number is traceable.** Each score stores the judge's prompt
   version, model, cost and full verdict next to the trajectory it judged.

## Where Dyno is weaker

- One model provider for judges (Anthropic), three judges, no sandboxes, no red
  teaming, no hosted sharing.
- Small scale: SQLite and a sequential runner. Fine for 50 cases x 3; not for
  thousands.
- Built and used by one person on two agents. The others have far more users finding
  their edge cases.
