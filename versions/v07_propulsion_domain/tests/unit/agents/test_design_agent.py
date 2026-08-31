import pytest

from agents.design_agent import DesignAgent, DesignProposalRejectedError
from config.settings import get_settings
from core.design.design_space import DesignSpace, DesignVariable
from core.models.registry import ModelRegistry
from core.requirements.schema import Objective, Requirements
from core.tools.registry import ToolRegistry


def _requirements():
    return Requirements(
        problem="test",
        domain="generic.mechanics",
        objectives=[Objective(name="obj", direction="maximize", metric="m")],
    )


def _space():
    return DesignSpace(
        domain="generic.mechanics",
        variables={"x": DesignVariable(name="x", lower_bound=0.0, upper_bound=10.0)},
    )


def _agent(scripted_provider):
    registry = ModelRegistry(get_settings(), scripted_provider)
    tools = ToolRegistry(get_settings().tools)
    return DesignAgent(registry, tools)


@pytest.mark.asyncio
async def test_accepts_proposal_within_bounds(scripted_provider):
    scripted_provider.queue("reasoning", {"values": {"x": 5.0}, "rationale": "mid-range"})
    agent = _agent(scripted_provider)
    values = await agent.propose(_requirements(), _space())
    assert values == {"x": 5.0}


@pytest.mark.asyncio
async def test_rejects_proposal_out_of_bounds(scripted_provider):
    scripted_provider.queue("reasoning", {"values": {"x": 999.0}, "rationale": "oops"})
    agent = _agent(scripted_provider)
    with pytest.raises(DesignProposalRejectedError):
        await agent.propose(_requirements(), _space())


@pytest.mark.asyncio
async def test_rejects_proposal_missing_variable(scripted_provider):
    scripted_provider.queue("reasoning", {"values": {}, "rationale": "forgot x"})
    agent = _agent(scripted_provider)
    with pytest.raises(DesignProposalRejectedError):
        await agent.propose(_requirements(), _space())


@pytest.mark.asyncio
async def test_empty_design_space_returns_empty_dict_without_calling_llm(scripted_provider):
    agent = _agent(scripted_provider)
    empty_space = DesignSpace(domain="d", variables={})
    values = await agent.propose(_requirements(), empty_space)
    assert values == {}
    assert scripted_provider.calls == []
