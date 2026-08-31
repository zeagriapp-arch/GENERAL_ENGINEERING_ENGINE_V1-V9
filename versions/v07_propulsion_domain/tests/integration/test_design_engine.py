"""
Vertical slice de Phase 4: Requirements -> Design Space -> Generator ->
Design Engine -> Physics/Simulation real (Phase 3, cold-gas thruster) ->
solo se devuelven diseños físicamente válidos que cumplen los requisitos.
"""
import pytest

from core.design.design_space import DesignSpace
from core.design.engine import DesignEngine
from core.design.generator import GridSweepGenerator, RandomSamplingGenerator
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


def _requirements(min_thrust: float = 0.8):
    return Requirements(
        problem="Explorar área de salida cumpliendo empuje mínimo",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        constraints=[Constraint(name="min_thrust", expression=f"thrust >= {min_thrust}", hard=True)],
        variables={
            "chamber_pressure": Parameter(name="chamber_pressure", value=5e5, unit="Pa", type=ParameterType.FIXED),
            "chamber_temperature": Parameter(name="chamber_temperature", value=300.0, unit="K", type=ParameterType.FIXED),
            "throat_area": Parameter(name="throat_area", value=1e-6, unit="m^2", type=ParameterType.FIXED),
            "nozzle_exit_area": Parameter(
                name="nozzle_exit_area", value=1e-5, unit="m^2", type=ParameterType.FREE, range=(1e-6, 5e-5)
            ),
            "ambient_pressure": Parameter(name="ambient_pressure", value=0.0, unit="Pa", type=ParameterType.FIXED),
            "gas_gamma": Parameter(name="gas_gamma", value=1.4, unit=None, type=ParameterType.FIXED),
            "gas_constant": Parameter(name="gas_constant", value=296.8, unit="J/(kg*K)", type=ParameterType.FIXED),
        },
    )


def test_grid_sweep_finds_valid_designs_meeting_hard_constraint():
    requirements = _requirements(min_thrust=0.8)
    space = DesignSpace.from_requirements(requirements)
    engine = DesignEngine()
    budget = Budget(max_iterations=10, max_simulations=10, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    result = engine.explore(requirements, space, GridSweepGenerator(), budget=budget, seed=1)

    assert len(result.valid_designs) > 0
    for candidate in result.valid_designs:
        assert candidate.results.predictions["thrust"] >= 0.8
        assert candidate.results.model_validity == "within_range"
        assert candidate.design.domain == "satellite.propulsion"


def test_rejected_designs_include_reasons():
    requirements = _requirements(min_thrust=0.8)
    space = DesignSpace.from_requirements(requirements)
    engine = DesignEngine()
    budget = Budget(max_iterations=10, max_simulations=10, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    result = engine.explore(requirements, space, GridSweepGenerator(), budget=budget, seed=1)

    assert len(result.rejected_designs) > 0
    for rejected in result.rejected_designs:
        assert len(rejected.reasons) > 0


def test_impossible_constraint_rejects_everything():
    """thrust >= 100 es físicamente imposible para este thruster — ningún candidato debe pasar."""
    requirements = _requirements(min_thrust=100.0)
    space = DesignSpace.from_requirements(requirements)
    engine = DesignEngine()
    budget = Budget(max_iterations=5, max_simulations=5, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    result = engine.explore(requirements, space, GridSweepGenerator(), budget=budget, seed=1)

    assert len(result.valid_designs) == 0
    assert len(result.rejected_designs) == 5


def test_random_and_grid_generators_are_interchangeable():
    """Ambas estrategias deben implementar la misma interfaz sin cambiar el DesignEngine."""
    requirements = _requirements(min_thrust=0.8)
    space = DesignSpace.from_requirements(requirements)
    engine = DesignEngine()
    budget = Budget(max_iterations=8, max_simulations=8, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    grid_result = engine.explore(requirements, space, GridSweepGenerator(), budget=budget, seed=1)
    random_result = engine.explore(requirements, space, RandomSamplingGenerator(), budget=budget, seed=1)

    assert grid_result.iterations == 8
    assert random_result.iterations == 8
    assert len(grid_result.valid_designs) > 0
    assert len(random_result.valid_designs) > 0


def test_budget_limits_exploration():
    requirements = _requirements(min_thrust=0.8)
    space = DesignSpace.from_requirements(requirements)
    engine = DesignEngine()
    budget = Budget(max_iterations=3, max_simulations=100, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    result = engine.explore(requirements, space, GridSweepGenerator(), budget=budget, seed=1)

    assert result.iterations == 3
    assert len(result.valid_designs) + len(result.rejected_designs) == 3


def test_no_solver_registered_rejects_all_with_insufficient_evidence():
    simulation_engine.unregister_all()  # override del fixture: sin solver
    requirements = _requirements()
    space = DesignSpace.from_requirements(requirements)
    engine = DesignEngine()
    budget = Budget(max_iterations=3, max_simulations=3, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    result = engine.explore(requirements, space, GridSweepGenerator(), budget=budget, seed=1)

    assert len(result.valid_designs) == 0
    assert all("model_validity=unknown" in r.reasons[0] for r in result.rejected_designs)
