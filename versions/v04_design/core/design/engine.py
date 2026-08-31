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

from core.design.design_space import DesignSpace
from core.design.generator import DesignGenerator
from core.design.repository import create
from core.design.schema import Design
from core.experiments.schema import Results
from core.orchestrator.budget import Budget, BudgetTracker
from core.physics.schema import ConstraintKind, ConstraintStatus, PhysicsConstraint
from core.requirements.schema import Parameter, ParameterType, Requirements
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
    def _build_design(
        self, requirements: Requirements, design_space: DesignSpace, candidate_values: dict[str, float]
    ) -> Design:
        parameters: dict[str, Parameter] = dict(design_space.fixed_parameters)
        for name, value in candidate_values.items():
            var = design_space.variables[name]
            parameters[name] = Parameter(
                name=name,
                value=value,
                unit=var.unit,
                type=ParameterType.FREE,
                range=(var.lower_bound, var.upper_bound),
                source=var.source,
            )
        return create(
            domain=requirements.domain,
            parameters=parameters,
            constraints=requirements.constraints,
            objectives=requirements.objectives,
            provenance=[f"design_space:{requirements.problem}"],
        )

    def _check_design_space_constraints(self, design_space: DesignSpace, candidate_values: dict[str, float]) -> list[str]:
        violations: list[str] = []
        full_values = design_space.all_values_with(candidate_values)
        for name, var in design_space.variables.items():
            for expr, kind, label in (
                (var.constraint, ConstraintKind.BOUND, "constraint"),
                (var.manufacturing_constraint, ConstraintKind.NUMERICAL, "manufacturing_constraint"),
            ):
                if not expr:
                    continue
                pc = PhysicsConstraint(name=f"{name}.{label}", kind=kind, expression=expr)
                if pc.evaluate(full_values) == ConstraintStatus.VIOLATED:
                    violations.append(f"{name}: {label} violado ({expr})")
        return violations

    def _evaluate_requirements(self, requirements: Requirements, results: Results) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if results.model_validity != "within_range":
            reasons.append(f"model_validity={results.model_validity} — sin evidencia física suficiente")
            return False, reasons

        hard_violated = False
        for constraint in requirements.constraints:
            pc = PhysicsConstraint(name=constraint.name, kind=ConstraintKind.PHYSICAL, expression=constraint.expression)
            status = pc.evaluate(results.predictions)
            if status == ConstraintStatus.VIOLATED:
                reasons.append(f"constraint violado: {constraint.name} ({constraint.expression})")
                hard_violated = hard_violated or constraint.hard
            elif status == ConstraintStatus.UNKNOWN:
                reasons.append(f"constraint no evaluable: {constraint.name} ({constraint.expression})")
                hard_violated = hard_violated or constraint.hard

        return (not hard_violated), reasons

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

            design = self._build_design(requirements, design_space, candidate_values)

            pre_violations = self._check_design_space_constraints(design_space, candidate_values)
            if pre_violations:
                rejected.append(CandidateEvaluation(design=design, results=None, passed=False, reasons=pre_violations))
                continue

            # Una vez comprometido el candidato (record_iteration ya se
            # llamó), se completa su evaluación SIEMPRE — nunca se corta a
            # mitad de camino, o el candidato "desaparecería" sin quedar
            # registrado ni en válidos ni en rechazados.
            tracker.record_simulation()
            results = simulation_engine.run(design)
            passed, reasons = self._evaluate_requirements(requirements, results)
            evaluation = CandidateEvaluation(design=design, results=results, passed=passed, reasons=reasons)
            (valid if passed else rejected).append(evaluation)

        stopping_reason = "computational_budget_exceeded" if tracker.exceeded() else "candidates_exhausted"
        return ExplorationResult(
            valid_designs=valid,
            rejected_designs=rejected,
            iterations=tracker.iterations,
            stopping_reason=stopping_reason,
        )
