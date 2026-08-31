import pytest

from config.settings import get_settings
from core.requirements.schema import Parameter, ParameterType
from core.tools.interfaces import ToolNotFoundError, ToolPermissionError
from core.tools.registry import ToolRegistry


@pytest.fixture
def registry():
    return ToolRegistry(get_settings().tools)


def test_get_tools_for_agent_filters_by_permission(registry):
    tools = registry.get_tools_for_agent("simulation_agent")
    names = {t.name for t in tools}
    assert "run_simulation" in names
    assert "save_experiment" not in names  # solo orchestrator


@pytest.mark.asyncio
async def test_invoke_allowed_tool_succeeds(registry):
    result = await registry.invoke(
        "validate_units",
        {"parameters": {"area": Parameter(name="area", value=1e-5, unit="m^2", type=ParameterType.FREE)}},
        caller="design_agent",
    )
    assert result.ok
    assert result.value == []  # sin errores dimensionales


@pytest.mark.asyncio
async def test_invoke_denied_for_unauthorized_agent(registry):
    with pytest.raises(ToolPermissionError):
        await registry.invoke("save_experiment", {}, caller="simulation_agent")


@pytest.mark.asyncio
async def test_invoke_unknown_tool_raises(registry):
    with pytest.raises(ToolNotFoundError):
        await registry.invoke("does_not_exist", {}, caller="orchestrator")
