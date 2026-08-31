"""
Phase 5: verifica que OptunaOptimizer ejecuta búsqueda matemática real
(no LLM) sobre el Design Space del cold-gas thruster (Phase 3/4),
respeta constraints duros, y produce un Pareto front coherente en el
caso multi-objetivo.
"""
import pytest

from core.design.design_space import DesignSpace
from core.optimization.optuna_backend import MissingObjectiveMetricError, OptunaOptimizer
from core.orchestrator.budget import Budget
from core.requirements.schema import Constraint, Objective, Parameter, ParameterType, Requirements
from core.simulation import engine as simulation_engine
from domains.satellite.propulsion.simulation_adapters.cold_gas_solver import ColdGasNozzleSolver


@pytest.fixture(autouse=True)
def _register_cold_gas_solver():
    simulation_engine.unregister_all()
    simulation_engine.register_solver("satellite.propulsion", ColdGasNozzleSolver())
    yield
    simulation_engine.unregister_all()


def _base_variables():
    return {
        "chamber_pressure": Parameter(name="chamber_pressure", value=5e5, unit="Pa", type=ParameterType.FIXED),
        "chamber_temperature": Parameter(name="chamber_temperature", value=300.0, unit="K", type=ParameterType.FIXED),
        "throat_area": Parameter(name="throat_area", value=1e-6, unit="m^2", type=ParameterType.FIXED),
        "nozzle_exit_area": Parameter(
            name="nozzle_exit_area", value=1e-5, unit="m^2", type=ParameterType.FREE, range=(1e-6, 5e-5)
        ),
        "ambient_pressure": Parameter(name="ambient_pressure", value=0.0, unit="Pa", type=ParameterType.FIXED),
        "gas_gamma": Parameter(name="gas_gamma", value=1.4, unit=None, type=ParameterType.FIXED),
        "gas_constant": Parameter(name="gas_constant", value=296.8, unit="J/(kg*K)", type=ParameterType.FIXED),
    }


def _single_objective_requirements(min_thrust=0.8):
    return Requirements(
        problem="Maximizar Isp sujeto a empuje mínimo",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        constraints=[Constraint(name="min_thrust", expression=f"thrust >= {min_thrust}", hard=True)],
        variables=_base_variables(),
    )


def _budget(n=25):
    return Budget(max_iterations=n, max_simulations=n, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)


def test_single_objective_finds_near_optimal_isp():
    """Isp crece monótonamente con area_ratio en vacío -> el óptimo debe acercarse al límite superior."""
    req = _single_objective_requirements()
    space = DesignSpace.from_requirements(req)
    result = OptunaOptimizer().optimize(req, space, budget=_budget(30), seed=42)

    assert result.iterations == 30
    assert len(result.best_designs) == 1
    best = result.best_designs[0]
    assert best.passed
    assert best.objective_values["isp"] > 76.0  # cerca del máximo teórico (~76.96 en area=5e-5)
    assert best.design.parameters["nozzle_exit_area"].value > 4e-5  # cerca del límite superior


def test_pruned_trials_never_appear_as_best():
    req = _single_objective_requirements(min_thrust=100.0)  # físicamente imposible
    space = DesignSpace.from_requirements(req)
    result = OptunaOptimizer().optimize(req, space, budget=_budget(10), seed=1)

    assert len(result.best_designs) == 0
    assert all(not e.passed for e in result.all_evaluations)


def test_all_evaluations_include_reasons_for_failures():
    req = _single_objective_requirements(min_thrust=0.8)
    space = DesignSpace.from_requirements(req)
    result = OptunaOptimizer().optimize(req, space, budget=_budget(15), seed=1)

    failed = [e for e in result.all_evaluations if not e.passed]
    assert all(len(e.reasons) > 0 for e in failed)


def test_multi_objective_produces_pareto_front():
    req = Requirements(
        problem="Maximizar Isp y empuje simultáneamente",
        domain="satellite.propulsion",
        objectives=[
            Objective(name="isp", direction="maximize", metric="specific_impulse"),
            Objective(name="thrust", direction="maximize", metric="thrust"),
        ],
        variables=_base_variables(),
    )
    space = DesignSpace.from_requirements(req)
    result = OptunaOptimizer().optimize(req, space, budget=_budget(20), seed=7)

    assert len(result.best_designs) >= 1
    for candidate in result.best_designs:
        assert "isp" in candidate.objective_values
        assert "thrust" in candidate.objective_values


def test_raises_when_objective_metric_missing_from_results():
    req = Requirements(
        problem="objetivo inexistente",
        domain="satellite.propulsion",
        objectives=[Objective(name="bogus", direction="maximize", metric="does_not_exist")],
        variables=_base_variables(),
    )
    space = DesignSpace.from_requirements(req)
    with pytest.raises(MissingObjectiveMetricError):
        OptunaOptimizer().optimize(req, space, budget=_budget(3), seed=1)


def test_budget_limits_search():
    req = _single_objective_requirements()
    space = DesignSpace.from_requirements(req)
    result = OptunaOptimizer().optimize(req, space, budget=_budget(5), seed=1)
    assert result.iterations == 5
    assert len(result.all_evaluations) == 5
