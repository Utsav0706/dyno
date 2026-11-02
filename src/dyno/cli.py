"""The `dyno` command. Each milestone adds its commands here (run, report, compare,
gate, cluster, label, calibrate, import-failures).

Typer, not argparse: commands and options come from type-hinted functions, so the CLI
and its --help can't drift apart, and CliRunner tests it without a subprocess.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from dyno import __version__
from dyno.agent import AgentResult, get_agent
from dyno.cases import load_suite
from dyno.config import get_settings
from dyno.log import setup_logging
from dyno.runner import run_suite
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
) -> None:
    """Run every case in a suite k times and store each attempt and its steps."""
    suite = load_suite(suite_path)
    agent_name = agent or suite.agent
    if not agent_name:
        raise typer.BadParameter("no agent: pass --agent or set 'agent' in the suite")
    repeats = k or suite.k
    store = Store(open_engine(get_settings().database_url))

    total = len(suite.cases) * repeats
    done = 0

    def progress(case_id: str, attempt: int, result: AgentResult, latency_ms: float) -> None:
        nonlocal done
        done += 1
        status = f"error: {result.error}" if result.error else f"{len(result.steps)} steps"
        typer.echo(
            f"[{done}/{total}] {case_id} #{attempt}  {status}  {latency_ms / 1000:.1f}s", err=True
        )

    s = run_suite(
        suite,
        get_agent(agent_name),
        agent_name=agent_name,
        k=repeats,
        store=store,
        on_attempt=progress,
    )
    typer.echo(
        f"run {s.run_id}: {s.suite} x{s.k} with {s.agent}: {s.attempts} attempts, "
        f"{s.errors} errors, {s.input_tokens}+{s.output_tokens} tokens, "
        f"GBP {s.cost_gbp:.4f}, {s.seconds:.1f}s"
    )


if __name__ == "__main__":
    app()
