import pytest

from agents.simulation_agent import SimulationAgent
from config.settings import get_settings
from core.design.repository import create
from core.models.registry import ModelRegistry
from core.requirements.schema import Parameter, ParameterType
from core.simulation import engine as simulation_engine
from core.tools.registry import ToolRegistry
from domains.satellite.propulsion.simulation_adapters.cold_gas_solver import ColdGasNozzleSolver


@pytest.fixture(autouse=True)
def _register_solver():
    simulation_engine.unregister_all()
    simulation_engine.register_solver("satellite.propulsion", ColdGasNozzleSolver())
    yield
    simulation_engine.unregister_all()


def _design():
    values = {
        "chamber_pressure": 5e5,
        "chamber_temperature": 300.0,
        "throat_area": 1e-6,
        "nozzle_exit_area": 1e-5,
        "ambient_pressure": 0.0,
        "gas_gamma": 1.4,
        "gas_constant": 296.8,
    }
    return create(
        domain="satellite.propulsion",
        parameters={n: Parameter(name=n, value=v, type=ParameterType.FIXED) for n, v in values.items()},
    )


@pytest.mark.asyncio
async def test_simulation_agent_never_calls_llm(scripted_provider):
    """El Simulation Agent no razona — no debe invocar ModelProvider.complete en absoluto."""
    registry = ModelRegistry(get_settings(), scripted_provider)
    tools = ToolRegistry(get_settings().tools)
    agent = SimulationAgent(registry, tools)

    results = await agent.simulate(_design())

    assert scripted_provider.calls == []
    assert results.model_validity == "within_range"
    assert "thrust" in results.predictions


@pytest.mark.asyncio
async def test_simulation_agent_only_authorized_for_its_own_tool(scripted_provider):
    """El Tool Registry debe rechazar cualquier tool fuera de las autorizadas para simulation_agent."""
    from core.tools.interfaces import ToolPermissionError

    registry = ModelRegistry(get_settings(), scripted_provider)
    tools = ToolRegistry(get_settings().tools)
    agent = SimulationAgent(registry, tools)

    with pytest.raises(ToolPermissionError):
        await agent.invoke_tool("save_experiment", {})
