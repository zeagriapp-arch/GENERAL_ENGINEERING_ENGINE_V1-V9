"""
Design Engine (Phase 4): Requirements -> Design Space -> Design Generator
-> Candidate Design -> Physics/Simulation (Phase 3) -> Validation ->
PASS (store) / FAIL (descartar con razones explícitas).

NO es optimización matemática (Phase 5) ni generación vía LLM (Phase 6):
es la capacidad de explorar un espacio acotado y devolver únicamente
configuraciones físicamente válidas que cumplen los requisitos.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from core.design.candidate import build_design, check_design_space_constraints, evaluate_requirements
from core.design.design_space import DesignSpace
from core.design.generator import DesignGenerator
from core.design.schema import Design
from core.experiments.schema import Results
from core.orchestrator.budget import Budget, BudgetTracker
from core.requirements.schema import Requirements
from core.simulation import engine as simulation_engine


class CandidateEvaluation(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    design: Design
    results: Optional[Results] = None
    passed: bool
    reasons: list[str] = []


class ExplorationResult(BaseModel):
    valid_designs: list[CandidateEvaluation]
    rejected_designs: list[CandidateEvaluation]
    iterations: int
    stopping_reason: str


class DesignEngine:
    def explore(
        self,
        requirements: Requirements,
        design_space: DesignSpace,
        generator: DesignGenerator,
        *,
        budget: Budget,
        seed: Optional[int] = None,
    ) -> ExplorationResult:
        tracker = BudgetTracker(budget)
        candidates = generator.generate(design_space, n=budget.max_iterations, seed=seed)

        valid: list[CandidateEvaluation] = []
        rejected: list[CandidateEvaluation] = []

        for candidate_values in candidates:
            if tracker.exceeded():
                break
            tracker.record_iteration()

            design = build_design(requirements, design_space, candidate_values)

            pre_violations = check_design_space_constraints(design_space, candidate_values)
            if pre_violations:
                rejected.append(CandidateEvaluation(design=design, results=None, passed=False, reasons=pre_violations))
                continue

            # Una vez comprometido el candidato (record_iteration ya se
            # llamó), se completa su evaluación SIEMPRE — nunca se corta a
            # mitad de camino, o el candidato "desaparecería" sin quedar
            # registrado ni en válidos ni en rechazados (bug real
            # encontrado por los tests de integración).
            tracker.record_simulation()
            results = simulation_engine.run(design)
            passed, reasons = evaluate_requirements(requirements, results)
            evaluation = CandidateEvaluation(design=design, results=results, passed=passed, reasons=reasons)
            (valid if passed else rejected).append(evaluation)

        stopping_reason = "computational_budget_exceeded" if tracker.exceeded() else "candidates_exhausted"
        return ExplorationResult(
            valid_designs=valid,
            rejected_designs=rejected,
            iterations=tracker.iterations,
            stopping_reason=stopping_reason,
        )
