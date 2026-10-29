"""The `dyno` command. Each milestone adds its commands here (run, report, compare,
gate, cluster, label, calibrate, import-failures).

Typer, not argparse: commands and options come from type-hinted functions, so the CLI
and its --help can't drift apart, and CliRunner tests it without a subprocess.
"""

from __future__ import annotations

import typer

from dyno import __version__
from dyno.config import get_settings
from dyno.log import setup_logging

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


if __name__ == "__main__":
    app()
