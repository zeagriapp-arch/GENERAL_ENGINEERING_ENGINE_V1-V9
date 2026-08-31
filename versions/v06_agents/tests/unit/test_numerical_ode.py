import pytest

from core.numerical.interfaces import ConvergenceStatus
from core.numerical.ode import ODESolver


def test_exponential_decay_converges_and_matches_analytical():
    """dy/dt = -y, y(0)=1 -> y(t) = exp(-t)."""
    solver = ODESolver()
    result = solver.solve(
        {"fun": lambda t, y: [-y[0]], "y0": [1.0], "t_span": (0.0, 2.0), "t_eval": [2.0], "rtol": 1e-10, "atol": 1e-12}
    )
    assert result.convergence_status == ConvergenceStatus.CONVERGED
    y_final = result.values["y"][0][-1]
    import math

    assert y_final == pytest.approx(math.exp(-2.0), rel=1e-6)


def test_invalid_function_returns_failed_not_exception():
    solver = ODESolver()
    result = solver.solve({"fun": "not_callable", "y0": [1.0], "t_span": (0.0, 1.0)})
    assert result.convergence_status == ConvergenceStatus.FAILED
    assert len(result.errors) > 0


def test_reports_runtime():
    solver = ODESolver()
    result = solver.solve({"fun": lambda t, y: [-y[0]], "y0": [1.0], "t_span": (0.0, 1.0), "t_eval": [1.0]})
    assert result.runtime_seconds is not None
    assert result.runtime_seconds >= 0
