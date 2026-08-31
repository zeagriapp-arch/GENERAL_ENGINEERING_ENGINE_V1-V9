"""
Vertical slice de Phase 8: Requirements -> DesignSpace -> Optimizer ->
CADA candidato guardado como Experiment -> Report del mejor. Física real
del cold-gas thruster.
"""
import pytest

from core.design.design_space import DesignSpace
from core.experiments.store import SQLiteExperimentStore
from core.optimization.optuna_backend import OptunaOptimizer
from core.orchestrator.budget import Budget
from core.orchestrator.discovery import run_discovery_mode
from core.simulation import engine as simulation_engine
from domains.satellite.propulsion.requirements_schema import build_cold_gas_requirements
from domains.satellite.propulsion.simulation_adapters.cold_gas_solver import ColdGasNozzleSolver


@pytest.fixture(autouse=True)
def _register_solver():
    simulation_engine.unregister_all()
    simulation_engine.register_solver("satellite.propulsion", ColdGasNozzleSolver())
    yield
    simulation_engine.unregister_all()


def _budget(n=15):
    return Budget(max_iterations=n, max_simulations=n, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)


def test_discovery_mode_produces_report_for_best_candidate(tmp_path):
    requirements = build_cold_gas_requirements("Maximizar Isp", min_thrust=0.5)
    space = DesignSpace.from_requirements(requirements)
    store = SQLiteExperimentStore(tmp_path / "discovery.db")

    result = run_discovery_mode(requirements, space, OptunaOptimizer(), store, budget=_budget(15), seed=1)

    assert result.total_evaluated == 15
    assert result.total_valid > 0
    assert result.report is not None
    assert result.report.results["thrust"] >= 0.5
    assert result.report.constraints_status["min_thrust"] == "SATISFIED"


def test_every_candidate_is_persisted_not_just_the_best(tmp_path):
    requirements = build_cold_gas_requirements("Maximizar Isp", min_thrust=0.5)
    space = DesignSpace.from_requirements(requirements)
    store = SQLiteExperimentStore(tmp_path / "discovery2.db")

    result = run_discovery_mode(requirements, space, OptunaOptimizer(), store, budget=_budget(10), seed=1)

    assert len(result.experiment_graph.nodes) == 10  # todos los evaluados, no solo el mejor


def test_impossible_requirement_yields_no_report_but_still_persists_attempts(tmp_path):
    requirements = build_cold_gas_requirements("Empuje imposible", min_thrust=1000.0)
    space = DesignSpace.from_requirements(requirements)
    store = SQLiteExperimentStore(tmp_path / "discovery3.db")

    result = run_discovery_mode(requirements, space, OptunaOptimizer(), store, budget=_budget(5), seed=1)

    assert result.report is None  # nunca se inventa un ganador sin evidencia
    assert result.total_valid == 0
    assert len(result.experiment_graph.nodes) == 5  # los intentos SÍ quedan registrados


def test_report_reproducibility_flag_is_true_for_registered_domain(tmp_path):
    requirements = build_cold_gas_requirements("Maximizar Isp", min_thrust=0.5)
    space = DesignSpace.from_requirements(requirements)
    store = SQLiteExperimentStore(tmp_path / "discovery4.db")

    result = run_discovery_mode(requirements, space, OptunaOptimizer(), store, budget=_budget(10), seed=1)

    assert result.report.reproducible is True
    assert result.report.model_used == "cold_gas_thruster_ideal_nozzle"
