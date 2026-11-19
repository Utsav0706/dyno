from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scout_eval_setup.py"


@pytest.fixture
def setup_module(monkeypatch: pytest.MonkeyPatch):
    # Scout isn't installed in Dyno's environment: fake its corpus loader.
    corpus = types.ModuleType("scout.eval.corpus")
    corpus.load_corpus = lambda folder: [("a.pdf", b"%PDF-1")]  # type: ignore[attr-defined]
    for name in ("scout", "scout.eval"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "scout.eval.corpus", corpus)
    spec = importlib.util.spec_from_file_location("scout_eval_setup", SCRIPT)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def scout_checkout(tmp_path: Path) -> Path:
    scout = tmp_path / "scout"
    scout.mkdir()
    base = {
        "llm": {"base_url": None, "models": {"plan": "x"}},
        "jobs": {"max_per_hour_per_user": 10},
        "telemetry": {"max_field_chars": 4000},
    }
    (scout / "config.yaml").write_text(yaml.safe_dump(base))
    return scout


def test_direct_keeps_scouts_model_calls_as_they_are(setup_module, tmp_path: Path) -> None:
    setup_module.main(scout_checkout(tmp_path), tmp_path / "out")
    config = yaml.safe_load((tmp_path / "out" / "config.eval.yaml").read_text())
    assert config["llm"]["base_url"] is None
    assert config["jobs"]["max_per_hour_per_user"] == 1000
    assert config["telemetry"]["max_field_chars"] == 20_000
    assert (tmp_path / "out" / "corpus" / "a.pdf").read_bytes() == b"%PDF-1"


def test_via_gearbox_points_scouts_model_calls_at_it(setup_module, tmp_path: Path) -> None:
    setup_module.main(scout_checkout(tmp_path), tmp_path / "out", "http://127.0.0.1:8002")
    config = yaml.safe_load((tmp_path / "out" / "config.eval.yaml").read_text())
    assert config["llm"] == {"base_url": "http://127.0.0.1:8002", "models": {"plan": "x"}}
