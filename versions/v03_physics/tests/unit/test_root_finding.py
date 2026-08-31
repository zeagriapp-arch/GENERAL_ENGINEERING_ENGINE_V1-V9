import pytest

from core.numerical.root_finding import RootNotBracketedError, solve_scalar_root


def test_solves_simple_linear_root():
    result = solve_scalar_root(lambda x: x - 3.0, bracket=(0.0, 10.0))
    assert result.root == pytest.approx(3.0)
    assert result.converged


def test_solves_nonlinear_root():
    result = solve_scalar_root(lambda x: x**2 - 4.0, bracket=(0.0, 10.0))
    assert result.root == pytest.approx(2.0)


def test_raises_when_not_bracketed():
    with pytest.raises(RootNotBracketedError):
        solve_scalar_root(lambda x: x**2 + 1.0, bracket=(0.0, 10.0))
