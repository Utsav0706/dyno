import io
import json
import logging

from typer.testing import CliRunner

from dyno import __version__
from dyno.cli import app
from dyno.config import Settings
from dyno.log import setup_logging

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"dyno {__version__}"


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert "Usage" in result.output and "version" in result.output


def test_settings_defaults_and_empty_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    s = Settings(_env_file=None)
    assert s.database_url == "sqlite:///dyno.db"
    assert s.anthropic_api_key is None


def test_json_logs_with_extra_fields():
    stream = io.StringIO()
    setup_logging("INFO", stream)
    logging.getLogger("dyno.test").info("case done", extra={"case_id": "web-1", "passed": True})
    record = json.loads(stream.getvalue().splitlines()[0])
    assert record["msg"] == "case done"
    assert record["case_id"] == "web-1" and record["passed"] is True
