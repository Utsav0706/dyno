from pathlib import Path

import pytest

from dyno.store import Store, open_engine

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_SUITE = ROOT / "examples" / "example_suite.yaml"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    # A file, not :memory: — each new connection to :memory: is a different empty database.
    return f"sqlite:///{(tmp_path / 'dyno.db').as_posix()}"


@pytest.fixture
def store(db_url: str) -> Store:
    return Store(open_engine(db_url))
