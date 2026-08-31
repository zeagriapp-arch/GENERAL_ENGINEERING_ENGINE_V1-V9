"""
Discovery Mode / Optimization Mode (sección 23).

Decisión ya tomada en el Architecture Design Document (sección 1,
decisión #5): "Optimization Mode = Discovery Mode con baseline_design ya
fijado". En V1, con un único PhysicsModel por dominio, ambos modos
comparten la misma implementación — la diferencia real (explorar
arquitecturas alternativas vs. afinar una ya elegida) aparecerá cuando
haya más de un PhysicsModel por dominio (Phase 9+).

Esta función es el "pegamento" que faltaba: conecta DesignSpace (Phase 4)
+ Optimizer (Phase 5) + ExperimentStore (Phase 1) + Report Generator
(Phase 8) en un solo ciclo ejecutable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.design.design_space import DesignSpace
from core.experiments.schema import Experiment, ExperimentGraph, ExperimentStatus, Verdict
from core.experiments.store import ExperimentStore
from core.optimization.interfaces import Optimizer
from core.orchestrator.budget import Budget
from core.orchestrator.report import Report, generate_report
from core.requirements.schema import Requirements


@dataclass
class DiscoveryModeResult:
    report: Optional[Report]
    experiment_graph: ExperimentGraph
    total_evaluated: int
    total_valid: int
    stopping_reason: str


def run_discovery_mode(
    requirements: Requirements,
    design_space: DesignSpace,
    optimizer: Optimizer,
    store: ExperimentStore,
    *,
    budget: Budget,
    seed: Optional[int] = None,
) -> DiscoveryModeResult:
    """
    Ejecuta la búsqueda completa, persiste CADA candidato evaluado (no
    solo el mejor — sección 22, Experiment Graph) y genera el Report del
    mejor candidato encontrado. Si ninguno tuvo evidencia suficiente,
    devuelve `report=None` en vez de inventar un ganador.
    """
    result = optimizer.optimize(requirements, design_space, budget=budget, seed=seed)

    root_id: Optional[str] = None
    previous_id: Optional[str] = None
    candidate_to_experiment_id: dict[int, str] = {}

    for candidate in result.all_evaluations:
        status = ExperimentStatus.ACCEPTED if candidate.passed else ExperimentStatus.REJECTED
        verdict = Verdict(decision="ACCEPT" if candidate.passed else "REJECT", findings=candidate.reasons)
        experiment = Experiment(
            parent_id=previous_id,
            requirements=requirements,
            design=candidate.design,
            results=candidate.results,
            verdict=verdict,
            status=status,
        )
        store.save(experiment)
        candidate_to_experiment_id[id(candidate)] = experiment.id
        if root_id is None:
            root_id = experiment.id
        previous_id = experiment.id

    graph = store.get_graph(root_id) if root_id else ExperimentGraph(root_id="none", nodes={}, edges=[])
    total_valid = sum(1 for c in result.all_evaluations if c.passed)

    report: Optional[Report] = None
    if result.best_designs:
        best = result.best_designs[0]
        best_experiment = store.get(candidate_to_experiment_id[id(best)])
        report = generate_report(best_experiment, graph)

    return DiscoveryModeResult(
        report=report,
        experiment_graph=graph,
        total_evaluated=len(result.all_evaluations),
        total_valid=total_valid,
        stopping_reason=result.stopping_reason,
    )
