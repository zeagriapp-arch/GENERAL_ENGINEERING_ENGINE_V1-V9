"""
Orchestrator básico (Phase 1).

Ejecuta el ciclo RESEARCH -> DESIGN -> SIMULATE -> ANALYZE -> CRITIQUE ->
(OPTIMIZE) -> DECIDE, aplicando siempre el Budget (sección 35) y
guardando cada paso en el Experiment Store (sección 21).

IMPORTANTE (Phase 1): Physics/Simulation/Evaluation/Critic Engines reales
llegan en Phase 3/4/5, y los agentes LLM reales en Phase 6. Por eso este
Orchestrator recibe los "steps" como funciones inyectadas (dependency
injection, sección 36) con defaults que devuelven explícitamente
UNKNOWN / INSUFFICIENT EVIDENCE — nunca inventan un resultado. Esto es
el Principio Fundamental (sección 2) aplicado incluso antes de que exista
física real: sin evidencia, el sistema no afirma nada.

Simplificación deliberada de V1: `run()` es síncrono. Se vuelve async en
Phase 6 cuando los steps invoquen agentes LLM reales (I/O real). El
contrato de la interfaz (`Orchestrator` en el Architecture Design
Document) se mantiene: mismo input -> mismo tipo de output.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from core.design.repository import clone, create
from core.design.schema import Design
from core.experiments.schema import (
    Experiment,
    ExperimentGraph,
    ExperimentStatus,
    EvaluationResult,
    Results,
    Verdict,
)
from core.experiments.store import ExperimentStore
from core.orchestrator.budget import Budget, BudgetTracker, StoppingReason
from core.orchestrator.state import ProjectState
from core.requirements.schema import Requirements
from core.validation.dimensional_analysis import validate as validate_units

DesignStep = Callable[[ProjectState], Design]
SimulateStep = Callable[[Design], Results]
EvaluateStep = Callable[[Optional[Results], Results], EvaluationResult]
CritiqueStep = Callable[[Design, Results, EvaluationResult], Verdict]


def _default_design_step(state: ProjectState) -> Design:
    """Baseline trivial a partir de Requirements. Design Agent real = Phase 6."""
    if state.baseline_design is None:
        return create(domain=state.requirements.domain, parameters=dict(state.requirements.variables))
    return clone(state.baseline_design, as_child=True)


def _default_simulate_step(design: Design) -> Results:
    """Sin PhysicsModel/SimulationSolver todavía (Phase 3) -> UNKNOWN explícito."""
    return Results(model_validity="unknown", data_quality="unknown", confidence=None)


def _default_evaluate_step(baseline_results: Optional[Results], candidate_results: Results) -> EvaluationResult:
    return EvaluationResult(improved=None, confidence=None)


def _default_critique_step(design: Design, results: Results, evaluation: EvaluationResult) -> Verdict:
    """Sin evidencia real todavía -> REJECT explícito, nunca ACCEPT por defecto."""
    return Verdict(
        decision="REJECT",
        findings=["INSUFFICIENT EVIDENCE: no hay PhysicsModel/SimulationSolver registrado todavía (Phase 3+)."],
    )


@dataclass
class RunResult:
    final_state: ProjectState
    experiment_graph: ExperimentGraph
    stopping_reason: StoppingReason
    budget_tracker: BudgetTracker


class Orchestrator:
    def __init__(
        self,
        experiment_store: ExperimentStore,
        *,
        design_step: DesignStep = _default_design_step,
        simulate_step: SimulateStep = _default_simulate_step,
        evaluate_step: EvaluateStep = _default_evaluate_step,
        critique_step: CritiqueStep = _default_critique_step,
    ):
        self._store = experiment_store
        self._design_step = design_step
        self._simulate_step = simulate_step
        self._evaluate_step = evaluate_step
        self._critique_step = critique_step

    def run(self, requirements: Requirements, *, budget: Budget) -> RunResult:
        tracker = BudgetTracker(budget)
        state = ProjectState(requirements=requirements)

        # Gate obligatorio (sección 10): nada avanza con unidades inconsistentes.
        unit_errors = validate_units(requirements.variables)
        if unit_errors:
            state.record_note(f"Requirements rechazados por Dimensional Analysis: {unit_errors}")
            return RunResult(
                final_state=state,
                experiment_graph=ExperimentGraph(root_id="none", nodes={}, edges=[]),
                stopping_reason=StoppingReason.CONSTRAINT_VIOLATION,
                budget_tracker=tracker,
            )

        root_id: Optional[str] = None
        previous_experiment_id: Optional[str] = None
        baseline_results: Optional[Results] = None
        stopping_reason = StoppingReason.STILL_RUNNING

        while not tracker.exceeded():
            tracker.record_iteration()
            state.iteration = tracker.iterations

            design = self._design_step(state)
            if state.baseline_design is None:
                state.baseline_design = design
            state.current_design = design

            tracker.record_simulation()
            results = self._simulate_step(design)

            evaluation = self._evaluate_step(baseline_results, results)
            verdict = self._critique_step(design, results, evaluation)

            # IMPORTANTE: el parent_id del Experiment enlaza con el Experiment
            # anterior en este run (Experiment Graph, sección 22) — NO con
            # design.parent_id, que es un concepto distinto (linaje de Design,
            # útil para Design Agent/Optimizer, pero un UUID no relacionado con
            # los ids de Experiment).
            experiment = Experiment(
                parent_id=previous_experiment_id,
                requirements=requirements,
                design=design,
                results=results,
                metrics=evaluation,
                verdict=verdict,
                status=ExperimentStatus.ACCEPTED if verdict.decision == "ACCEPT" else ExperimentStatus.REJECTED,
            )
            self._store.save(experiment)
            state.current_experiment_id = experiment.id
            state.experiment_history.append(experiment.id)
            state.record_note(f"Experiment {experiment.id}: verdict={verdict.decision} findings={verdict.findings}")

            if root_id is None:
                root_id = experiment.id
            previous_experiment_id = experiment.id
            if baseline_results is None:
                baseline_results = results

            if verdict.decision == "REJECT" and "INSUFFICIENT EVIDENCE" in " ".join(verdict.findings):
                stopping_reason = StoppingReason.INSUFFICIENT_EVIDENCE
                break
            if verdict.decision == "REJECT":
                stopping_reason = StoppingReason.CONSTRAINT_VIOLATION
                break
            if evaluation.improved is False:
                stopping_reason = StoppingReason.NO_IMPROVEMENT
                break

        if stopping_reason == StoppingReason.STILL_RUNNING and tracker.exceeded():
            stopping_reason = StoppingReason.BUDGET_EXCEEDED

        graph = self._store.get_graph(root_id) if root_id else ExperimentGraph(root_id="none", nodes={}, edges=[])
        return RunResult(
            final_state=state,
            experiment_graph=graph,
            stopping_reason=stopping_reason,
            budget_tracker=tracker,
        )
