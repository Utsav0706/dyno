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
    assert "12 attempts, 2 errors" in last
    run_id = last.split()[1].rstrip(":")
    run = Store(open_engine(db_url)).get_run(run_id)
    assert run.agent == "example" and len(run.results) == 12


def test_run_needs_an_agent(monkeypatch, db_url, tmp_path):
    suite = tmp_path / "s.yaml"
    suite.write_text("cases:\n  - {id: a, input: q}\n", encoding="utf-8")
    result = _invoke(monkeypatch, db_url, str(suite))
    assert result.exit_code != 0
    assert "no agent" in result.output
