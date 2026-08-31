"""
Agent Orchestrator (Phase 6): mismo ciclo que `core.orchestrator.Orchestrator`
(Phase 1) pero con agentes LLM reales en vez de steps stub — por eso es
async (los agentes hacen I/O real hacia el ModelProvider).

Vive en `agents/`, NO en `core/orchestrator/`: importa agentes
concretos, y `core` nunca puede importar `agents` (regla de arquitectura
verificada por `lint-imports` desde Phase 0). `core.orchestrator.Orchestrator`
sigue siendo válido para steps sync/deterministas (tests, scripts sin LLM).
Reutiliza Budget/ProjectState/ExperimentStore de Phase 1 sin modificarlos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agents.analysis_agent import AnalysisAgent
from agents.critic_agent import CriticAgent
from agents.design_agent import DesignAgent, DesignProposalRejectedError
from agents.research_agent import ResearchAgent
from agents.schemas import ResearchFindings
from agents.simulation_agent import SimulationAgent
from core.design.candidate import build_design
from core.design.design_space import DesignSpace
from core.experiments.schema import Experiment, ExperimentGraph, ExperimentStatus, Results
from core.experiments.store import ExperimentStore
from core.models.registry import ModelRegistry
from core.orchestrator.budget import Budget, BudgetTracker, StoppingReason
from core.orchestrator.state import ProjectState
from core.requirements.schema import Requirements
from core.tools.interfaces import ToolProvider
from core.validation.dimensional_analysis import validate as validate_units


@dataclass
class AsyncRunResult:
    final_state: ProjectState
    experiment_graph: ExperimentGraph
    stopping_reason: StoppingReason
    budget_tracker: BudgetTracker
    research_findings: Optional[ResearchFindings] = None


class AsyncOrchestrator:
    def __init__(self, experiment_store: ExperimentStore, model_registry: ModelRegistry, tool_registry: ToolProvider):
        self._store = experiment_store
        self._research_agent = ResearchAgent(model_registry, tool_registry)
        self._design_agent = DesignAgent(model_registry, tool_registry)
        self._simulation_agent = SimulationAgent(model_registry, tool_registry)
        self._analysis_agent = AnalysisAgent(model_registry, tool_registry)
        self._critic_agent = CriticAgent(model_registry, tool_registry)

    async def run(self, requirements: Requirements, design_space: DesignSpace, *, budget: Budget) -> AsyncRunResult:
        tracker = BudgetTracker(budget)
        state = ProjectState(requirements=requirements)

        unit_errors = validate_units(requirements.variables)
        if unit_errors:
            state.record_note(f"Requirements rechazados por Dimensional Analysis: {unit_errors}")
            return AsyncRunResult(
                final_state=state,
                experiment_graph=ExperimentGraph(root_id="none", nodes={}, edges=[]),
                stopping_reason=StoppingReason.CONSTRAINT_VIOLATION,
                budget_tracker=tracker,
            )

        tracker.record_llm_call()
        tracker.record_research_call()
        findings = await self._research_agent.research(requirements)
        state.record_note(f"Research: notes={findings.notes} open_questions={findings.open_questions}")

        root_id: Optional[str] = None
        previous_experiment_id: Optional[str] = None
        baseline_results: Optional[Results] = None
        stopping_reason = StoppingReason.STILL_RUNNING

        while not tracker.exceeded():
            tracker.record_iteration()
            state.iteration = tracker.iterations

            tracker.record_llm_call()
            try:
                candidate_values = await self._design_agent.propose(requirements, design_space)
            except DesignProposalRejectedError as exc:
                state.record_note(f"Propuesta del Design Agent rechazada (iteración {state.iteration}): {exc}")
                continue  # cuenta contra el budget, no genera Experiment

            design = build_design(requirements, design_space, candidate_values)
            if state.baseline_design is None:
                state.baseline_design = design
            state.current_design = design

            tracker.record_simulation()
            results = await self._simulation_agent.simulate(design)

            evaluation = self._analysis_agent.compute_evaluation(requirements, baseline_results, results)
            if baseline_results is not None:
                tracker.record_llm_call()
                narrative = await self._analysis_agent.narrate(requirements, evaluation)
                state.record_note(f"Analysis: {narrative}")

            tracker.record_llm_call()
            verdict = await self._critic_agent.critique(requirements, design, results)

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
            if baseline_results is None:
                baseline_results = results
            previous_experiment_id = experiment.id

            if verdict.decision == "REJECT":
                stopping_reason = StoppingReason.CONSTRAINT_VIOLATION
                break
            if evaluation.improved is False:
                stopping_reason = StoppingReason.NO_IMPROVEMENT
                break

        if stopping_reason == StoppingReason.STILL_RUNNING and tracker.exceeded():
            stopping_reason = StoppingReason.BUDGET_EXCEEDED

        graph = self._store.get_graph(root_id) if root_id else ExperimentGraph(root_id="none", nodes={}, edges=[])
        return AsyncRunResult(
            final_state=state,
            experiment_graph=graph,
            stopping_reason=stopping_reason,
            budget_tracker=tracker,
            research_findings=findings,
        )
