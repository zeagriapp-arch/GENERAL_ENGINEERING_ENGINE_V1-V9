import pytest

from core.validation.regression_store import RegressionStore


@pytest.fixture
def store(tmp_path):
    return RegressionStore(tmp_path / "regressions.json")


def test_first_run_is_not_a_regression(store):
    result = store.check("bench-1", {"position": 19.6})
    assert result.is_first_run
    assert not result.regression_detected


def test_matching_result_after_record_is_not_regression(store):
    store.record("bench-1", {"position": 19.6})
    result = store.check("bench-1", {"position": 19.6})
    assert not result.regression_detected
    assert not result.is_first_run


def test_diverging_result_is_regression(store):
    store.record("bench-1", {"position": 19.6})
    result = store.check("bench-1", {"position": 25.0}, threshold=1e-6)
    assert result.regression_detected
    assert result.difference["position"] > 0
