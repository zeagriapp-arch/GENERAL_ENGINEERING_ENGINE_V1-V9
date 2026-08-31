"""
Test explícito anti-infinite-loop (sección 35): un critique_step que
SIEMPRE acepta y SIEMPRE dice "mejoró" no debe poder correr para
siempre — el Budget debe cortar el loop.
"""
from core.design.repository import clone
from core.experiments.schema import EvaluationResult, Results, Verdict
from core.experiments.store import SQLiteExperimentStore
from core.orchestrator.budget import Budget, StoppingReason
from core.orchestrator.orchestrator import Orchestrator
from core.requirements.schema import Objective, Parameter, ParameterType, Requirements


def _requirements():
    return Requirements(
        problem="test anti-loop",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        variables={
            "area": Parameter(name="area", value=1e-5, unit="m^2", type=ParameterType.FREE, range=(1e-6, 1e-2)),
        },
    )


def _always_accept_simulate(design):
    return Results(predictions={"isp": 100.0}, confidence=0.9, model_validity="within_range", data_quality="high")


def _always_improved_evaluate(baseline, candidate):
    return EvaluationResult(improved=True, confidence=0.9)


def _always_accept_critique(design, results, evaluation):
    return Verdict(decision="ACCEPT", findings=[])


def test_orchestrator_stops_at_max_iterations(tmp_path):
    store = SQLiteExperimentStore(tmp_path / "budget_test.db")
    orch = Orchestrator(
        store,
        simulate_step=_always_accept_simulate,
        evaluate_step=_always_improved_evaluate,
        critique_step=_always_accept_critique,
    )
    budget = Budget(max_iterations=5, max_simulations=100, max_llm_calls=100, max_runtime_seconds=60, max_research_calls=100)

    result = orch.run(_requirements(), budget=budget)

    assert result.stopping_reason == StoppingReason.BUDGET_EXCEEDED
    assert result.budget_tracker.iterations == 5
    assert len(result.experiment_graph.nodes) == 5


def test_orchestrator_respects_max_simulations_even_if_iterations_higher(tmp_path):
    store = SQLiteExperimentStore(tmp_path / "budget_test2.db")
    orch = Orchestrator(
        store,
        simulate_step=_always_accept_simulate,
        evaluate_step=_always_improved_evaluate,
        critique_step=_always_accept_critique,
    )
    budget = Budget(max_iterations=1000, max_simulations=3, max_llm_calls=1000, max_runtime_seconds=60, max_research_calls=1000)

    result = orch.run(_requirements(), budget=budget)

    assert result.stopping_reason == StoppingReason.BUDGET_EXCEEDED
    assert result.budget_tracker.simulations == 3
