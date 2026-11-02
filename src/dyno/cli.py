"""The `dyno` command. Each milestone adds its commands here (run, report, compare,
gate, cluster, label, calibrate, import-failures).

Typer, not argparse: commands and options come from type-hinted functions, so the CLI
and its --help can't drift apart, and CliRunner tests it without a subprocess.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from dyno import __version__
from dyno.agent import AgentResult, get_agent
from dyno.cases import load_suite
from dyno.config import get_settings
from dyno.log import setup_logging
from dyno.report import build_report, to_markdown
from dyno.runner import rescore_run, run_suite
from dyno.scoring import Score, attempt_passed, build_scorers
from dyno.store import Store, open_engine

app = typer.Typer(
    help="Run an agent on test cases, record every step, score it, compare runs, gate CI.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    setup_logging(get_settings().log_level)


@app.command()
def version() -> None:
    """Print Dyno's version."""
    typer.echo(f"dyno {__version__}")


@app.command()
def run(
    suite_path: Annotated[Path, typer.Argument(help="Suite YAML file.", exists=True)],
    agent: Annotated[
        str | None,
        typer.Option("--agent", "-a", help="Agent name or module:Attribute (default: suite's)."),
    ] = None,
    k: Annotated[
        int | None, typer.Option("--k", min=1, help="Attempts per case (default: suite's k).")
    ] = None,
    tags: Annotated[
        list[str] | None, typer.Option("--tags", help="Only cases with any of these tags.")
    ] = None,
    ids: Annotated[list[str] | None, typer.Option("--ids", help="Only these case ids.")] = None,
) -> None:
    """Run every case in a suite k times; score and store each attempt and its steps.

    --tags and --ids repeat: `--ids a --ids b`.
    """
    try:
        suite = load_suite(suite_path).select(tags=tags, ids=ids)
        scorers = build_scorers(suite.scorers)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    agent_name = agent or suite.agent
    if not agent_name:
        raise typer.BadParameter("no agent: pass --agent or set 'agent' in the suite")
    repeats = k or suite.k
    store = _store()
    try:
        # Adapters connect (and Scout signs up) here: fail before any case runs.
        the_agent = get_agent(agent_name)
    except Exception as exc:
        typer.echo(f"agent {agent_name!r} failed to start: {exc}", err=True)
        raise typer.Exit(1) from exc

    total = len(suite.cases) * repeats
    done = 0

    def progress(
        case_id: str, attempt: int, result: AgentResult, latency_ms: float, scores: dict[str, Score]
    ) -> None:
        nonlocal done
        done += 1
        verdict = {True: "pass", False: "FAIL", None: "n/a"}[
            attempt_passed([sc.passed for sc in scores.values()])
        ]
        failed = [name for name, sc in scores.items() if sc.passed is False]
        if result.error:
            why = f" (agent error: {result.error[:120]})"
        else:
            why = f" ({', '.join(failed)})" if failed else ""
        typer.echo(
            f"[{done}/{total}] {case_id} #{attempt}  {verdict}{why}  {latency_ms / 1000:.1f}s",
            err=True,
        )

    s = run_suite(
        suite,
        the_agent,
        agent_name=agent_name,
        k=repeats,
        store=store,
        scorers=scorers,
        on_attempt=progress,
    )
    typer.echo(
        f"run {s.run_id}: {s.suite} x{s.k} with {s.agent}: {s.attempts} attempts, "
        f"{s.passed} passed, {s.errors} errors, {s.input_tokens}+{s.output_tokens} tokens, "
        f"GBP {s.cost_gbp:.6f}, {s.seconds:.1f}s"
    )


@app.command()
def score(run_id: Annotated[str, typer.Argument(help="Run id from `dyno run`.")]) -> None:
    """Re-score a stored run with its own scorer settings (free: the agent isn't called)."""
    try:
        n = rescore_run(_store(), run_id)
    except LookupError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"re-scored {n} attempts in run {run_id}")


class Format(StrEnum):
    md = "md"
    json = "json"


@app.command()
def report(
    run_id: Annotated[str, typer.Argument(help="Run id from `dyno run`.")],
    format: Annotated[Format, typer.Option("--format", "-f")] = Format.md,
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write to a file.")] = None,
) -> None:
    """Report a run: per-scorer pass rates, pass@k / pass^k, cost, tags, failures."""
    run = _store().get_run(run_id)
    if run is None:
        typer.echo(f"no run {run_id!r}", err=True)
        raise typer.Exit(1)
    rep = build_report(run)
    text = to_markdown(rep) if format is Format.md else rep.model_dump_json(indent=2) + "\n"
    if out:
        out.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {out}", err=True)
    else:
        typer.echo(text, nl=False)


def _store() -> Store:
    return Store(open_engine(get_settings().database_url))


if __name__ == "__main__":
    app()
