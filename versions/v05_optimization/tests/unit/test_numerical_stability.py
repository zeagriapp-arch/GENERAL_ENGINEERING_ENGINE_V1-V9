import numpy as np

from core.numerical.stability import check_array_stability


def test_stable_array_passes():
    result = check_array_stability(np.array([1.0, 2.0, 3.0]))
    assert result.stable
    assert result.notes == []


def test_nan_detected():
    result = check_array_stability(np.array([1.0, float("nan"), 3.0]))
    assert not result.stable
    assert any("NaN" in n for n in result.notes)


def test_inf_detected():
    result = check_array_stability(np.array([1.0, float("inf")]))
    assert not result.stable
    assert any("Inf" in n for n in result.notes)
