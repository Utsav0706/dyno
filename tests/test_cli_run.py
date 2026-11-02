import json

from typer.testing import CliRunner

from conftest import EXAMPLE_SUITE
from dyno.cli import app
from dyno.config import get_settings
from dyno.store import Store, open_engine

runner = CliRunner()


def _invoke(monkeypatch, db_url, *args):
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    try:
        return runner.invoke(app, ["run", *args])
    finally:
        get_settings.cache_clear()


def test_run_command_end_to_end(monkeypatch, db_url):
    result = _invoke(monkeypatch, db_url, str(EXAMPLE_SUITE), "--k", "2")
    assert result.exit_code == 0, result.output
    last = result.stdout.strip().splitlines()[-1]
    assert "12 attempts, 6 passed, 2 errors" in last
    run_id = last.split()[1].rstrip(":")
    run = Store(open_engine(db_url)).get_run(run_id)
    assert run.agent == "example" and len(run.results) == 12


def test_run_needs_an_agent(monkeypatch, db_url, tmp_path):
    suite = tmp_path / "s.yaml"
    suite.write_text("cases:\n  - {id: a, input: q}\n", encoding="utf-8")
    result = _invoke(monkeypatch, db_url, str(suite))
    assert result.exit_code != 0
    assert "no agent" in result.output


def _run_example(monkeypatch, db_url) -> str:
    result = _invoke(monkeypatch, db_url, str(EXAMPLE_SUITE))
    assert result.exit_code == 0, result.output
    return result.stdout.strip().splitlines()[-1].split()[1].rstrip(":")


def _cmd(monkeypatch, db_url, *args):
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    try:
        return runner.invoke(app, list(args))
    finally:
        get_settings.cache_clear()


def test_report_markdown_json_and_file(monkeypatch, db_url, tmp_path):
    run_id = _run_example(monkeypatch, db_url)
    md = _cmd(monkeypatch, db_url, "report", run_id)
    assert md.exit_code == 0 and md.stdout.startswith("# Dyno report: example")
    js = _cmd(monkeypatch, db_url, "report", run_id, "--format", "json")
    assert json.loads(js.stdout)["run_id"] == run_id
    out = tmp_path / "r.md"
    assert _cmd(monkeypatch, db_url, "report", run_id, "-o", str(out)).exit_code == 0
    assert "## Failures" in out.read_text(encoding="utf-8")


def test_score_and_report_unknown_run(monkeypatch, db_url):
    run_id = _run_example(monkeypatch, db_url)
    assert "re-scored 6 attempts" in _cmd(monkeypatch, db_url, "score", run_id).stdout
    assert _cmd(monkeypatch, db_url, "score", "nope").exit_code == 1
    assert _cmd(monkeypatch, db_url, "report", "nope").exit_code == 1


def test_bad_scorer_fails_before_running(monkeypatch, db_url, tmp_path):
    suite = tmp_path / "s.yaml"
    suite.write_text("agent: example\nscorers: [nope]\ncases:\n  - {id: a, input: q}\n")
    result = _invoke(monkeypatch, db_url, str(suite))
    assert result.exit_code != 0 and "unknown scorer" in result.output


def test_run_with_ids_and_agent_that_cannot_start(monkeypatch, db_url):
    result = _invoke(monkeypatch, db_url, str(EXAMPLE_SUITE), "--ids", "math-add", "--k", "2")
    assert result.exit_code == 0 and "2 attempts, 2 passed" in result.stdout
    monkeypatch.setenv("GEARBOX_URL", "http://127.0.0.1:9")  # nothing listens on port 9
    bad = _invoke(monkeypatch, db_url, str(EXAMPLE_SUITE), "--agent", "gearbox")
    assert bad.exit_code == 1 and "failed to start" in bad.output
