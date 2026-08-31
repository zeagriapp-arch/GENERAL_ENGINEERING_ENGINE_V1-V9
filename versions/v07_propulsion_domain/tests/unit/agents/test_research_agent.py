import pytest

from agents.research_agent import ResearchAgent
from config.settings import get_settings
from core.models.registry import ModelRegistry
from core.requirements.schema import Objective, Requirements
from core.tools.registry import ToolRegistry


def _requirements():
    return Requirements(
        problem="throat area choked mass flow rate",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
    )


@pytest.mark.asyncio
async def test_research_agent_returns_structured_findings(scripted_provider, tmp_path, monkeypatch):
    from domains.satellite.propulsion.knowledge import seed_knowledge

    await seed_knowledge.seed(db_prefix=str(tmp_path / "kb"))
    kb_engine = await seed_knowledge.seed(db_prefix=str(tmp_path / "kb2"))
    from core.knowledge import engine as knowledge_engine_module

    knowledge_engine_module.set_default_engine(kb_engine)

    scripted_provider.queue(
        "reasoning",
        {"relevant_equations": ["eq-choked-mass-flow"], "notes": ["Flujo atorado en la garganta"], "open_questions": []},
    )

    registry = ModelRegistry(get_settings(), scripted_provider)
    tools = ToolRegistry(get_settings().tools)
    agent = ResearchAgent(registry, tools)

    findings = await agent.research(_requirements())

    assert findings.relevant_equations == ["eq-choked-mass-flow"]
    assert "Flujo atorado en la garganta" in findings.notes
    # verificar que efectivamente se llamó a la tool y se pasó role correcto
    assert scripted_provider.calls[0]["role"] == "reasoning"
