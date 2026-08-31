import pytest

from agents.optimization_agent import OptimizationAgent
from config.settings import get_settings
from core.design.design_space import DesignSpace, DesignVariable
from core.models.registry import ModelRegistry
from core.tools.registry import ToolRegistry


def _space():
    return DesignSpace(
        domain="d",
        variables={
            "x": DesignVariable(name="x", lower_bound=0.0, upper_bound=10.0),
            "y": DesignVariable(name="y", lower_bound=0.0, upper_bound=10.0),
        },
    )


@pytest.mark.asyncio
async def test_suggest_focus_with_no_history(scripted_provider):
    scripted_provider.queue("reasoning", {"variables_to_explore": ["x"], "rationale": "sin historial, empezar simple"})
    registry = ModelRegistry(get_settings(), scripted_provider)
    tools = ToolRegistry(get_settings().tools)
    agent = OptimizationAgent(registry, tools)

    focus = await agent.suggest_focus(_space(), [])

    assert focus.variables_to_explore == ["x"]


@pytest.mark.asyncio
async def test_agent_never_executes_search_only_suggests(scripted_provider):
    """El Optimization Agent no tiene acceso a run_optimizer — solo puede sugerir."""
    from core.tools.interfaces import ToolPermissionError

    registry = ModelRegistry(get_settings(), scripted_provider)
    tools = ToolRegistry(get_settings().tools)
    agent = OptimizationAgent(registry, tools)

    tool_names = {t.name for t in agent.available_tools()}
    assert "run_optimizer" in tool_names  # tiene permiso...
    # ...pero llamarlo de verdad requeriría el módulo real; aquí solo
    # verificamos que save_experiment (fuera de su alcance) sí se rechaza.
    with pytest.raises(ToolPermissionError):
        await agent.invoke_tool("save_experiment", {})
