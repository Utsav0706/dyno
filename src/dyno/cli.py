"""The `dyno` command: run, score, report, compare, gate, cluster, dashboard, import,
import-failures, label, calibrate.

Typer, not argparse: commands and options come from type-hinted functions, so the CLI
and its --help can't drift apart, and CliRunner tests it without a subprocess.
"""

from __future__ import annotations

import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from dyno import __version__
from dyno.agent import AgentResult, get_agent
from dyno.calibration import calibrate as run_calibration
from dyno.calibration import to_markdown as calibration_markdown
from dyno.cases import ScorerSpec, load_scorer_specs, load_suite
from dyno.cluster import cluster_failures
from dyno.cluster import to_markdown as clusters_markdown
from dyno.compare import compare_ids
from dyno.compare import to_markdown as comparison_markdown
from dyno.config import get_settings
from dyno.failures import read_failures, to_cases, write_cases
from dyno.gate import gate
from dyno.judge import JudgeError, current_judge, get_judge
from dyno.labelling import all_labels, claim_items, save_label, task_items
from dyno.log import setup_logging
from dyno.report import build_report, to_markdown
from dyno.runner import rescore_run, run_suite
from dyno.scoring import Score, Scorer, attempt_passed, build_scorers
from dyno.store import Store, open_engine
from dyno.store.transfer import import_runs

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
    cases: Annotated[
        Path | None,
        typer.Option("--cases", exists=True, help="Take the cases from this file instead."),
    ] = None,
) -> None:
    """Run every case in a suite k times; score and store each attempt and its steps.

    --tags and --ids repeat: `--ids a --ids b`. With --cases, the suite file holds only
    settings (agent, k, scorers) and the cases come from the other file.
    """
    try:
        suite = load_suite(suite_path, cases).select(tags=tags, ids=ids)
        scorers = _scorers(suite.scorers)
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
    _judge_spend()


@app.command()
def score(
    run_id: Annotated[str, typer.Argument(help="Run id from `dyno run`.")],
    suite_path: Annotated[
        Path | None,
        typer.Option("--suite", exists=True, help="Use this suite file's scorers instead."),
    ] = None,
) -> None:
    """Re-score a stored run without calling the agent.

    By default with the scorers the run used (free unless they include judges). With
    --suite, with that file's scorers: e.g. to add judge scores to an existing run.
    Other scorers' stored scores are kept.
    """
    try:
        scorers = _scorers(load_scorer_specs(suite_path)) if suite_path else None
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    try:
        n = rescore_run(_store(), run_id, scorers)
    except LookupError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"re-scored {n} attempts in run {run_id}")
    _judge_spend()


def _scorers(specs: list[ScorerSpec]) -> list[Scorer]:
    """Build scorers; if any are judges, check the judge can start before anything runs
    (a missing API key should stop the command, not turn every score into an error)."""
    scorers = build_scorers(specs)
    if any(getattr(s, "uses_judge", False) for s in scorers):
        try:
            get_judge()
        except JudgeError as exc:
            raise ValueError(f"judge scorers need the judge: {exc}") from exc
    return scorers


def _judge_spend() -> None:
    judge = current_judge()
    if judge is not None and judge.calls:
        typer.echo(
            f"judges: {judge.calls} calls, GBP {judge.spent_gbp:.6f} ({judge.model})", err=True
        )


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


@app.command("import")
def import_(
    paths: Annotated[list[Path], typer.Argument(help="Other dyno.db files.", exists=True)],
) -> None:
    """Copy runs from other Dyno databases (e.g. CI eval artifacts) into this one."""
    store = _store()
    for path in paths:
        imported, skipped = import_runs(f"sqlite:///{path.resolve().as_posix()}", store)
        typer.echo(
            f"{path}: imported {', '.join(imported) or 'nothing'}"
            + (f"; already here: {', '.join(skipped)}" if skipped else "")
        )


class LabelKind(StrEnum):
    task = "task"
    claims = "claims"


def _ask(question: str, choices: str) -> str:
    """One keypress-style answer (then Enter); repeats until it's one of `choices`."""
    while True:
        reply = typer.prompt(f"{question} [{'/'.join(choices)}]", default="", show_default=False)
        reply = reply.strip().lower()[:1]
        if reply and reply in choices:
            return reply
        typer.echo(f"  type one of: {', '.join(choices)}")


@app.command()
def label(
    kind: Annotated[LabelKind, typer.Argument(help="task: whole answers; claims: single claims.")],
    runs: Annotated[
        list[str] | None, typer.Option("--run", help="Only these runs (repeat). Default: all.")
    ] = None,
    n: Annotated[int, typer.Option("--n", min=1, help="How many to label this session.")] = 40,
) -> None:
    """Hand-label judged items, blind: the judge's verdict is never shown.

    Every label is saved at once: quit with q any time and run it again to carry on.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # a console that can't show "£" shows "?"
    store = _store()
    try:
        if kind is LabelKind.task:
            items: list = task_items(store, runs, n)
        else:
            items = claim_items(store, runs, n)
    except LookupError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if not items:
        typer.echo("Nothing left to label.")
        return
    yes_no = {"y": True, "n": False, "u": None}
    for i, item in enumerate(items, start=1):
        typer.echo("\n" + "=" * 78)
        typer.echo(f"[{i}/{len(items)}] {item.case_id} (attempt {item.attempt})\n")
        if kind is LabelKind.task:
            typer.echo(f"QUESTION\n  {item.question}\n\nKEY POINTS\n{item.key}\n")
            typer.echo(f"ANSWER\n{item.answer}\n")
            task = _ask("Task success: every key point given, none contradicted?", "ynsq")
            if task == "q":
                break
            if task == "s":
                continue
            quality = _ask("Quality 4+/5 (correct, helpful, clear)?", "ynq")
            if quality == "q":
                break
            note = typer.prompt("Note (Enter to skip)", default="", show_default=False)
            save_label(store, item.result_id, "task_rubric", yes_no[task], note=note)
            save_label(store, item.result_id, "quality", yes_no[quality], note=note)
        else:
            typer.echo(f"CLAIM\n  {item.claim}\n\nEVIDENCE")
            for text in item.excerpts:
                typer.echo(f"  ---\n  {text}")
            verdict = _ask("\nDoes this evidence support the claim? (u = unsure)", "ynusq")
            if verdict == "q":
                break
            if verdict == "s":
                continue
            note = typer.prompt("Note (Enter to skip)", default="", show_default=False)
            save_label(
                store, item.result_id, "hallucination", yes_no[verdict], item=item.claim, note=note
            )
    typer.echo("\nSaved. Run `dyno calibrate` to compare with the judge.")


@app.command()
def calibrate(
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write to a file.")] = None,
) -> None:
    """Cohen's kappa between each judge and your labels, with every disagreement."""
    results = run_calibration(all_labels(_store()))
    if not results:
        typer.echo("No labels yet: run `dyno label task` first.", err=True)
        raise typer.Exit(1)
    text = calibration_markdown(results)
    if out:
        out.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {out}", err=True)
    for c in results:
        kappa = "n/a" if c.kappa is None else f"{c.kappa:.2f}"
        status = "trusted" if c.trusted else "BELOW 0.6"
        typer.echo(f"{c.scorer}: {c.n} labels, kappa {kappa} ({status})")


@app.command()
def compare(
    run_a: Annotated[str, typer.Argument(help="The earlier run (baseline).")],
    run_b: Annotated[str, typer.Argument(help="The later run.")],
    scorer: Annotated[
        str | None,
        typer.Option(help="Judge newly failing/passing cases by this scorer only."),
    ] = None,
    format: Annotated[Format, typer.Option("--format", "-f")] = Format.md,
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write to a file.")] = None,
) -> None:
    """Per-metric changes and newly failing / flaky / passing cases, on shared cases."""
    try:
        comparison = compare_ids(_store(), run_a, run_b, scorer)
    except LookupError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if format is Format.md:
        text = comparison_markdown(comparison)
    else:
        text = comparison.model_dump_json(indent=2) + "\n"
    _emit(text, out)


@app.command("gate")
def gate_cmd(
    candidate: Annotated[str, typer.Argument(help="The run to judge.")],
    baseline: Annotated[str, typer.Option("--baseline", help="The run to compare against.")],
    max_drop: Annotated[
        float, typer.Option("--max-drop", help="Largest allowed drop, in percentage points.")
    ] = 2.0,
    metric: Annotated[
        str,
        typer.Option(help="attempt_pass_rate, pass_at_k, pass_hat_k or a scorer name."),
    ] = "attempt_pass_rate",
    no_new_failures: Annotated[
        bool, typer.Option("--no-new-failures", help="Also fail if any passing case now fails.")
    ] = False,
) -> None:
    """Exit 0 if the candidate holds up against the baseline, 1 if it got worse."""
    try:
        result = gate(
            candidate,
            baseline,
            max_drop=max_drop,
            metric=metric,
            no_new_failures=no_new_failures,
            store=_store(),
        )
    except LookupError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"{'PASS' if result.passed else 'FAIL'}: {result.reason}")
    if result.newly_failing:
        typer.echo(f"newly failing: {', '.join(result.newly_failing)}")
    raise typer.Exit(0 if result.passed else 1)


@app.command()
def cluster(
    runs: Annotated[list[str], typer.Argument(help="One or more run ids.")],
    scorer: Annotated[
        str | None, typer.Option(help="Only failures of this scorer (default: any).")
    ] = None,
    format: Annotated[Format, typer.Option("--format", "-f")] = Format.md,
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write to a file.")] = None,
) -> None:
    """Group failures by what went wrong and name each group (needs the cluster extra)."""
    store = _store()
    loaded = [store.get_run(r) for r in runs]
    missing = [r for r, run in zip(runs, loaded, strict=True) if run is None]
    if missing:
        raise typer.BadParameter(f"no run {', '.join(missing)}")
    try:
        result = cluster_failures([r for r in loaded if r is not None], scorer=scorer)
    except (RuntimeError, JudgeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    text = (
        clusters_markdown(result)
        if format is Format.md
        else result.model_dump_json(indent=2) + "\n"
    )
    _emit(text, out)


@app.command("import-failures")
def import_failures(
    path: Annotated[
        Path, typer.Argument(help="Production failures, one JSON per line.", exists=True)
    ],
    out: Annotated[Path, typer.Option("--out", "-o", help="Case file to write.")],
    existing: Annotated[
        list[Path] | None,
        typer.Option("--existing", exists=True, help="Skip inputs already in this suite (repeat)."),
    ] = None,
) -> None:
    """Turn logged production failures into new cases (a YAML file for --cases)."""
    try:
        failures = read_failures(path)
        known: set[str] = set()
        for suite_path in existing or []:
            known |= {c.input for c in load_suite(suite_path).cases}
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    pairs, dropped = to_cases(failures, known)
    write_cases(pairs, out)
    typer.echo(f"{len(pairs)} new cases -> {out} ({dropped} repeats skipped)")


@app.command()
def dashboard(
    port: Annotated[int, typer.Option(help="Local port.")] = 8501,
) -> None:
    """Open the read-only dashboard on the store (needs the dashboard extra)."""
    import importlib.util
    import subprocess

    if importlib.util.find_spec("streamlit") is None:
        typer.echo('the dashboard needs the extra: pip install -e ".[dashboard]"', err=True)
        raise typer.Exit(1)
    script = Path(__file__).parent / "dashboard" / "app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(script), "--server.port", str(port)]
    cmd += ["--server.headless", "true", "--browser.gatherUsageStats", "false"]
    typer.echo(f"Dyno dashboard on http://localhost:{port} (Ctrl+C to stop)")
    raise typer.Exit(subprocess.call(cmd))


def _emit(text: str, out: Path | None) -> None:
    if out:
        out.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {out}", err=True)
    else:
        typer.echo(text, nl=False)


def _store() -> Store:
    return Store(open_engine(get_settings().database_url))


if __name__ == "__main__":
    app()
