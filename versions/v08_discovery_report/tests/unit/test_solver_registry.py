import pytest

from core.numerical.ode import ODESolver
from core.numerical.registry import NoSolverAvailableError, SolverRegistry
from core.numerical.root_finding import RootFindingSolver


@pytest.fixture
def registry():
    reg = SolverRegistry()
    reg.register(ODESolver())
    reg.register(RootFindingSolver())
    return reg


def test_get_by_id(registry):
    solver = registry.get("scipy-solve-ivp")
    assert solver.name.startswith("SciPy")


def test_get_missing_raises(registry):
    with pytest.raises(NoSolverAvailableError):
        registry.get("does-not-exist")


def test_find_for_problem_type(registry):
    ode_solvers = registry.find_for_problem_type("ode")
    assert len(ode_solvers) == 1
    assert ode_solvers[0].solver_id == "scipy-solve-ivp"

    root_solvers = registry.find_for_problem_type("root")
    assert len(root_solvers) == 1
    assert root_solvers[0].solver_id == "scipy-brentq-root"


def test_root_finding_solver_via_common_interface(registry):
    solver = registry.get("scipy-brentq-root")
    result = solver.solve({"func": lambda x: x**2 - 4.0, "bracket": (0.0, 10.0)})
    assert result.values["root"] == pytest.approx(2.0)
