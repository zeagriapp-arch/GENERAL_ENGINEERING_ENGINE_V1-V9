"""
Report Generator (sección 43): responde las 12 preguntas de "Definition
of Done for V1" a partir de un Experiment ya guardado. Determinista —
NO usa LLM. Un Report es una función pura de (Experiment, ExperimentGraph)
+ lo que esté registrado en el Simulation Engine en el momento de
generarlo (para poder nombrar el PhysicsModel usado).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from core.experiments.schema import Experiment, ExperimentGraph
from core.physics.schema import ConstraintKind, ConstraintStatus, PhysicsConstraint
from core.requirements.schema import ParameterType
from core.simulation import engine as simulation_engine


class Report(BaseModel):
    """Cada campo responde directamente una de las 12 preguntas de la sección 43."""

    experiment_id: str
    problem: str

    # 1. ¿Qué diseño evaluaste?
    design_summary: dict[str, float]

    # 2-3. ¿Qué variables cambiaste y por qué?
    changed_variables: dict[str, float]
    change_rationale: str

    # 4. ¿Qué modelo utilizaste?
    model_used: str
    model_version: str

    # 5. ¿Qué supuestos hiciste?
    assumptions: list[str]

    # 6. ¿Qué simulación ejecutaste?
    simulation_summary: str

    # 7. ¿Cuál fue el resultado?
    results: dict[str, float]

    # 8. ¿Qué incertidumbre existe?
    uncertainty: Optional[dict[str, float]]
    confidence: Optional[float]

    # 9. ¿Qué restricciones fueron satisfechas o violadas?
    constraints_status: dict[str, str]

    # 10. ¿Qué fuente respalda cada dato importante?
    sources: list[str]

    # 11. ¿Qué experimentos anteriores influyeron?
    prior_experiments: list[str]

    # 12. ¿Puede reproducirse el experimento?
    reproducible: bool
    reproducibility_notes: list[str]

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def summary_text(self) -> str:
        lines = [
            f"Experiment: {self.experiment_id} — {self.problem}",
            f"1-3. Diseño evaluado: {self.design_summary} | cambiadas: {self.changed_variables} ({self.change_rationale})",
            f"4. Modelo: {self.model_used} v{self.model_version}",
            f"5. Supuestos: {'; '.join(self.assumptions) if self.assumptions else '(ninguno registrado)'}",
            f"6. Simulación: {self.simulation_summary}",
            f"7. Resultado: {self.results}",
            f"8. Incertidumbre: {self.uncertainty} (confidence={self.confidence})",
            f"9. Constraints: {self.constraints_status}",
            f"10. Fuentes: {self.sources if self.sources else '(sin provenance registrada)'}",
            f"11. Experimentos previos: {self.prior_experiments if self.prior_experiments else '(ninguno — es la raíz)'}",
            f"12. Reproducible: {self.reproducible} — {'; '.join(self.reproducibility_notes)}",
        ]
        return "\n".join(lines)


def _ancestry_chain(experiment: Experiment, graph: ExperimentGraph) -> list[str]:
    chain: list[str] = []
    current_parent = experiment.parent_id
    seen: set[str] = set()
    while current_parent is not None and current_parent not in seen:
        chain.append(current_parent)
        seen.add(current_parent)
        parent_node = graph.nodes.get(current_parent)
        current_parent = parent_node.parent_id if parent_node else None
    return chain


def generate_report(experiment: Experiment, graph: ExperimentGraph) -> Report:
    design = experiment.design
    results = experiment.results

    design_summary = {
        name: p.value for name, p in design.parameters.items() if isinstance(p.value, (int, float))
    }
    changed_variables = {
        name: p.value
        for name, p in design.parameters.items()
        if p.type == ParameterType.FREE and isinstance(p.value, (int, float))
    }

    solver = simulation_engine.get_solver(design.domain)
    if solver is not None:
        model_used = solver.physics_model.name
        model_version = solver.physics_model.version
        assumptions = solver.physics_model.assumptions()
        reproducible = True
        reproducibility_notes = [
            "Modelo determinista, sin componentes estocásticos conocidos.",
            f"software_version={experiment.software_version}",
        ]
    else:
        model_used = "unknown"
        model_version = "unknown"
        assumptions = []
        reproducible = False
        reproducibility_notes = [
            "No hay un SimulationSolver registrado para este domain en el momento de generar el reporte "
            "— no se puede confirmar qué modelo produjo el resultado ni si es reproducible."
        ]

    if results is None:
        simulation_summary = "No se ejecutó ninguna simulación (Experiment sin Results)."
        results_dict: dict[str, float] = {}
        uncertainty = None
        confidence = None
    else:
        simulation_summary = (
            f"model_validity={results.model_validity}, data_quality={results.data_quality}, "
            f"confidence={results.confidence}"
        )
        results_dict = results.predictions
        uncertainty = results.uncertainty
        confidence = results.confidence

    constraints_status: dict[str, str] = {}
    if results is not None:
        for constraint in experiment.requirements.constraints:
            pc = PhysicsConstraint(name=constraint.name, kind=ConstraintKind.PHYSICAL, expression=constraint.expression)
            status = pc.evaluate(results.predictions)
            constraints_status[constraint.name] = status.value
    else:
        for constraint in experiment.requirements.constraints:
            constraints_status[constraint.name] = ConstraintStatus.UNKNOWN.value

    sources = list(design.provenance) + list(experiment.sources)
    prior_experiments = _ancestry_chain(experiment, graph)

    change_rationale = (
        "Primer diseño del experimento (baseline), sin variables previas para comparar."
        if not prior_experiments
        else "Variables libres modificadas respecto al experimento padre — ver Design Space / Optimizer para la estrategia usada."
    )

    return Report(
        experiment_id=experiment.id,
        problem=experiment.requirements.problem,
        design_summary=design_summary,
        changed_variables=changed_variables,
        change_rationale=change_rationale,
        model_used=model_used,
        model_version=model_version,
        assumptions=assumptions,
        simulation_summary=simulation_summary,
        results=results_dict,
        uncertainty=uncertainty,
        confidence=confidence,
        constraints_status=constraints_status,
        sources=sources,
        prior_experiments=prior_experiments,
        reproducible=reproducible,
        reproducibility_notes=reproducibility_notes,
    )
