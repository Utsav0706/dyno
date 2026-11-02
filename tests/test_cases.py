import pytest
from pydantic import ValidationError

from conftest import EXAMPLE_SUITE, FIXTURES
from dyno.cases import Suite, load_suite


def _suite(**case) -> Suite:
    return Suite.model_validate({"cases": [{"id": "a", "input": "q", **case}]})


def test_example_suite_loads():
    suite = load_suite(EXAMPLE_SUITE)
    assert suite.name == "example" and suite.agent == "example"
    assert len(suite.cases) == 6
    assert suite.cases[0].must_call == ["calculator"]


def test_scout_golden_format_loads():
    suite = load_suite(FIXTURES / "scout_golden_sample.yaml")
    assert suite.name == "scout_golden_sample"  # file name when the suite has none
    web, docs, none = suite.cases
    assert isinstance(web.expected, list) and len(web.expected) == 2
    assert docs.must_call == ["rag_search"]
    assert none.expected is None and none.tags == ["unanswerable"]


def test_typo_key_is_rejected():
    with pytest.raises(ValidationError, match="must_cal"):
        _suite(must_cal=["web_search"])


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate case ids"):
        Suite.model_validate({"cases": [{"id": "a", "input": "x"}, {"id": "a", "input": "y"}]})


def test_tool_in_both_lists_rejected():
    with pytest.raises(ValidationError, match="both must_call and must_not_call"):
        _suite(must_call=["t"], must_not_call=["t"])


def test_max_steps_must_be_positive():
    with pytest.raises(ValidationError):
        _suite(max_steps=0)


def test_load_rejects_non_mapping(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("- just a list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_suite(path)


def test_config_hash_tracks_what_runs():
    base = _suite(expected="x")
    assert base.config_hash("a", 1) == _suite(expected="x").config_hash("a", 1)
    assert base.config_hash("a", 1) != base.config_hash("a", 3)
    assert base.config_hash("a", 1) != base.config_hash("b", 1)
    assert base.config_hash("a", 1) != _suite(expected="y").config_hash("a", 1)
    renamed = base.model_copy(update={"name": "other"})
    assert renamed.config_hash("a", 1) == base.config_hash("a", 1)


def test_numeric_expected_becomes_text():
    assert _suite(expected=42).cases[0].expected == "42"
    assert _suite(expected=[1999, "GBP 3.60"]).cases[0].expected == ["1999", "GBP 3.60"]
