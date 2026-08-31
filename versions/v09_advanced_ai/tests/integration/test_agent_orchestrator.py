"""
Vertical slice de Phase 6: ciclo completo con los 6 agentes reales
(vía ScriptedModelProvider, sin Ollama) + física real del cold-gas
thruster (Phase 3). Verifica que el sistema nunca acepta un diseño solo
porque el LLM lo dice, y que una propuesta fuera de bounds del Design
Agent se rechaza sin romper el loop.
"""
import pytest

from agents.orchestrator import AsyncOrchestrator
from config.settings import get_settings
from core.design.design_space import DesignSpace
from core.experiments.schema import ExperimentStatus
from core.experiments.store import SQLiteExperimentStore
from core.models.registry import ModelRegistry
from core.orchestrator.budget import Budget, StoppingReason
from core.requirements.engine import RequirementsEngine
from core.requirements.schema import Constraint, Objective, Parameter, ParameterType
from core.simulation import engine as simulation_engine
from core.tools.registry import ToolRegistry
from domains.satellite.propulsion.simulation_adapters.cold_gas_solver import ColdGasNozzleSolver
from tests.unit.agents.conftest import ScriptedModelProvider


@pytest.fixture(autouse=True)
def _register_solver():
    simulation_engine.unregister_all()
    simulation_engine.register_solver("satellite.propulsion", ColdGasNozzleSolver())
    yield
    simulation_engine.unregister_all()


def _requirements(min_thrust=0.5):
    engine = RequirementsEngine()
    return engine.build(
        problem="Maximizar Isp sujeto a empuje mínimo",
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


def _build_orchestrator(provider, tmp_path):
    registry = ModelRegistry(get_settings(), provider)
    tools = ToolRegistry(get_settings().tools)
    store = SQLiteExperimentStore(tmp_path / "agent_orchestrator.db")
    return AsyncOrchestrator(store, registry, tools), store


@pytest.mark.asyncio
async def test_full_agent_cycle_with_valid_proposals(tmp_path):
    provider = ScriptedModelProvider(
        {
            "reasoning": [
                {"relevant_equations": ["eq-thrust-general"], "notes": ["contexto ok"], "open_questions": []},
                {"values": {"nozzle_exit_area": 2e-5}, "rationale": "primer intento"},
                {"findings": [], "risk_level": "LOW"},
            ]
        }
    )
    orchestrator, store = _build_orchestrator(provider, tmp_path)
    requirements = _requirements(min_thrust=0.5)
    space = DesignSpace.from_requirements(requirements)
    budget = Budget(max_iterations=1, max_simulations=5, max_llm_calls=20, max_runtime_seconds=30, max_research_calls=5)

    result = await orchestrator.run(requirements, space, budget=budget)

    assert len(result.final_state.experiment_history) == 1
    experiment = store.get(result.final_state.experiment_history[0])
    assert experiment.status == ExperimentStatus.ACCEPTED
    assert experiment.results.predictions["thrust"] >= 0.5
    assert experiment.design.parameters["nozzle_exit_area"].value == 2e-5


@pytest.mark.asyncio
async def test_design_agent_out_of_bounds_proposal_does_not_crash_loop(tmp_path):
    """Una propuesta inválida del Design Agent se descarta y el loop sigue con la siguiente iteración."""
    provider = ScriptedModelProvider(
        {
            "reasoning": [
                {"relevant_equations": [], "notes": [], "open_questions": []},
                {"values": {"nozzle_exit_area": 999.0}, "rationale": "propuesta inválida, fuera de rango"},
                {"values": {"nozzle_exit_area": 2e-5}, "rationale": "segundo intento, válido"},
                {"findings": [], "risk_level": "LOW"},
            ]
        }
    )
    orchestrator, store = _build_orchestrator(provider, tmp_path)
    requirements = _requirements(min_thrust=0.5)
    space = DesignSpace.from_requirements(requirements)
    budget = Budget(max_iterations=2, max_simulations=5, max_llm_calls=20, max_runtime_seconds=30, max_research_calls=5)

    result = await orchestrator.run(requirements, space, budget=budget)

    assert any("rechazada" in note for note in result.final_state.notes)
    assert len(result.final_state.experiment_history) == 1  # solo la propuesta válida generó Experiment


@pytest.mark.asyncio
async def test_critic_llm_optimism_never_overrides_physical_rejection(tmp_path):
    """Aunque el Critic LLM diga que todo está perfecto, un constraint duro violado siempre REJECT."""
    provider = ScriptedModelProvider(
        {
            "reasoning": [
                {"relevant_equations": [], "notes": [], "open_questions": []},
                {"values": {"nozzle_exit_area": 1e-6}, "rationale": "área mínima -> empuje bajo"},
                {"findings": ["todo perfecto, sin ningún problema"], "risk_level": "LOW"},
            ]
        }
    )
    orchestrator, store = _build_orchestrator(provider, tmp_path)
    # área mínima (1e-6 = throat_area, area_ratio=1) da el menor empuje posible;
    # min_thrust=100 es físicamente inalcanzable para este thruster.
    requirements = _requirements(min_thrust=100.0)
    space = DesignSpace.from_requirements(requirements)
    budget = Budget(max_iterations=5, max_simulations=5, max_llm_calls=20, max_runtime_seconds=30, max_research_calls=5)

    result = await orchestrator.run(requirements, space, budget=budget)

    assert result.stopping_reason == StoppingReason.CONSTRAINT_VIOLATION
    experiment = store.get(result.final_state.experiment_history[0])
    assert experiment.status == ExperimentStatus.REJECTED
    assert any("constraint violado" in f for f in experiment.verdict.findings)


@pytest.mark.asyncio
async def test_budget_tracks_llm_calls_not_just_iterations(tmp_path):
    provider = ScriptedModelProvider(
        {
            "reasoning": [
                {"relevant_equations": [], "notes": [], "open_questions": []},
                {"values": {"nozzle_exit_area": 2e-5}, "rationale": "ok"},
                {"findings": [], "risk_level": "LOW"},
            ]
        }
    )
    orchestrator, store = _build_orchestrator(provider, tmp_path)
    requirements = _requirements(min_thrust=0.5)
    space = DesignSpace.from_requirements(requirements)
    # research(1) + design(1) + critic(1) = 3 llamadas LLM para 1 iteración exitosa (sin baseline aún -> sin narrate)
    budget = Budget(max_iterations=5, max_simulations=5, max_llm_calls=3, max_runtime_seconds=30, max_research_calls=5)

    result = await orchestrator.run(requirements, space, budget=budget)

    assert result.budget_tracker.llm_calls == 3
