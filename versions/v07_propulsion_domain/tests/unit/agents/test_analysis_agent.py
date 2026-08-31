import pytest

from agents.analysis_agent import AnalysisAgent
from config.settings import get_settings
from core.experiments.schema import Results
from core.models.registry import ModelRegistry
from core.requirements.schema import Objective, Requirements
from core.tools.registry import ToolRegistry


def _requirements(direction="maximize"):
    return Requirements(
        problem="test",
        domain="d",
        objectives=[Objective(name="obj", direction=direction, metric="isp")],
    )


def _agent(scripted_provider):
    registry = ModelRegistry(get_settings(), scripted_provider)
    tools = ToolRegistry(get_settings().tools)
    return AnalysisAgent(registry, tools)


def test_compute_evaluation_no_baseline_returns_unknown_improved(scripted_provider):
    agent = _agent(scripted_provider)
    candidate = Results(predictions={"isp": 70.0}, confidence=0.9)
    evaluation = agent.compute_evaluation(_requirements(), None, candidate)
    assert evaluation.improved is None


def test_compute_evaluation_maximize_detects_improvement(scripted_provider):
    agent = _agent(scripted_provider)
    baseline = Results(predictions={"isp": 70.0}, confidence=0.9)
    candidate = Results(predictions={"isp": 75.0}, confidence=0.9)
    evaluation = agent.compute_evaluation(_requirements("maximize"), baseline, candidate)
    assert evaluation.improved is True
    assert evaluation.metric_deltas["isp"] == pytest.approx(5.0)


def test_compute_evaluation_minimize_direction(scripted_provider):
    agent = _agent(scripted_provider)
    baseline = Results(predictions={"isp": 70.0}, confidence=0.9)
    candidate = Results(predictions={"isp": 65.0}, confidence=0.9)
    evaluation = agent.compute_evaluation(_requirements("minimize"), baseline, candidate)
    assert evaluation.improved is True  # bajó, y el objetivo es minimizar


def test_compute_evaluation_never_calls_llm(scripted_provider):
    """Los deltas son deterministas — no deben requerir ninguna llamada al modelo."""
    agent = _agent(scripted_provider)
    baseline = Results(predictions={"isp": 70.0})
    candidate = Results(predictions={"isp": 75.0})
    agent.compute_evaluation(_requirements(), baseline, candidate)
    assert scripted_provider.calls == []


@pytest.mark.asyncio
async def test_narrate_uses_llm_and_returns_text(scripted_provider):
    scripted_provider.queue("reasoning", {"narrative": "El Isp mejoró levemente respecto al baseline."})
    agent = _agent(scripted_provider)
    baseline = Results(predictions={"isp": 70.0}, confidence=0.9)
    candidate = Results(predictions={"isp": 75.0}, confidence=0.9)
    evaluation = agent.compute_evaluation(_requirements(), baseline, candidate)

    narrative = await agent.narrate(_requirements(), evaluation)

    assert "mejoró" in narrative
