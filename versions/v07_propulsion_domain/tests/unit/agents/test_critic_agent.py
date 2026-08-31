import pytest

from agents.critic_agent import CriticAgent
from config.settings import get_settings
from core.design.repository import create
from core.experiments.schema import Results
from core.models.registry import ModelRegistry
from core.requirements.schema import Constraint, Objective, Parameter, ParameterType, Requirements
from core.tools.registry import ToolRegistry


def _requirements(min_thrust=0.5):
    return Requirements(
        problem="test",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        constraints=[Constraint(name="min_thrust", expression=f"thrust >= {min_thrust}", hard=True)],
    )


def _design():
    return create(domain="satellite.propulsion", parameters={"x": Parameter(name="x", value=1.0, type=ParameterType.FIXED)})


def _agent(scripted_provider):
    registry = ModelRegistry(get_settings(), scripted_provider)
    tools = ToolRegistry(get_settings().tools)
    return CriticAgent(registry, tools)


@pytest.mark.asyncio
async def test_llm_cannot_override_reject_to_accept(scripted_provider):
    """
    Aunque el LLM 'diga' que todo está bien, si model_validity != within_range
    o se viola un constraint duro, el veredicto SIEMPRE debe ser REJECT —
    la decisión se calcula ANTES de preguntarle nada al modelo.
    """
    scripted_provider.queue("reasoning", {"findings": ["todo se ve perfecto, sin problemas"], "risk_level": "LOW"})
    agent = _agent(scripted_provider)

    bad_results = Results(predictions={"thrust": 0.1}, model_validity="within_range")  # viola min_thrust=0.5
    verdict = await agent.critique(_requirements(min_thrust=0.5), _design(), bad_results)

    assert verdict.decision == "REJECT"
    assert any("constraint violado" in f for f in verdict.findings)


@pytest.mark.asyncio
async def test_llm_cannot_override_accept_to_reject_via_findings():
    """El LLM puede añadir hallazgos (concerns), pero eso no cambia la decisión determinista."""
    from tests.unit.agents.conftest import ScriptedModelProvider

    provider = ScriptedModelProvider({"reasoning": [{"findings": ["preocupación menor sobre supuestos"], "risk_level": "MEDIUM"}]})
    registry = ModelRegistry(get_settings(), provider)
    tools = ToolRegistry(get_settings().tools)
    agent = CriticAgent(registry, tools)

    good_results = Results(predictions={"thrust": 1.0}, model_validity="within_range")
    verdict = await agent.critique(_requirements(min_thrust=0.5), _design(), good_results)

    assert verdict.decision == "ACCEPT"
    assert any("[LLM, risk=MEDIUM]" in f for f in verdict.findings)


@pytest.mark.asyncio
async def test_unknown_model_validity_rejects_with_insufficient_evidence(scripted_provider):
    scripted_provider.queue("reasoning", {"findings": [], "risk_level": "LOW"})
    agent = _agent(scripted_provider)

    unknown_results = Results(predictions={}, model_validity="unknown")
    verdict = await agent.critique(_requirements(), _design(), unknown_results)

    assert verdict.decision == "REJECT"


@pytest.mark.asyncio
async def test_llm_findings_are_appended_not_replacing_deterministic_reasons(scripted_provider):
    scripted_provider.queue("reasoning", {"findings": ["hallazgo adicional del LLM"], "risk_level": "HIGH"})
    agent = _agent(scripted_provider)

    bad_results = Results(predictions={"thrust": 0.1}, model_validity="within_range")
    verdict = await agent.critique(_requirements(min_thrust=0.5), _design(), bad_results)

    assert any("constraint violado" in f for f in verdict.findings)  # determinista
    assert any("hallazgo adicional del LLM" in f for f in verdict.findings)  # LLM, añadido
