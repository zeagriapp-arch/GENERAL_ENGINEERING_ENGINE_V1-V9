"""
ValidationEngine (sección 24): corre las 6 verificaciones declaradas
(input validity, dimensional consistency, model validity, numerical
convergence, physical constraints, benchmark comparison) y produce un
ValidationReport único — nunca un simple True/False (sección 22).
"""
from __future__ import annotations

from core.numerical.interfaces import ConvergenceStatus
from core.physics.interfaces import PhysicsModel
from core.physics.schema import ConstraintStatus, PhysicsConstraint
from core.simulation.schema import ResultState, SimulationResult
from core.validation.schema import BenchmarkRunResult, ValidationReport


class ValidationEngine:
    def validate(
        self,
        sim_result: SimulationResult,
        *,
        physics_model: PhysicsModel | None = None,
        input_errors: list[str] | None = None,
        dimensional_errors: list[str] | None = None,
        constraints: list[PhysicsConstraint] | None = None,
        benchmark_result: BenchmarkRunResult | None = None,
    ) -> ValidationReport:
        input_errors = input_errors or []
        dimensional_errors = dimensional_errors or []
        notes: list[str] = []

        input_validity = len(input_errors) == 0
        notes += [f"[input] {e}" for e in input_errors]

        dimensional_consistency = len(dimensional_errors) == 0
        notes += [f"[dimensional] {e}" for e in dimensional_errors]

        model_validity = sim_result.status in (ResultState.SUCCESS, ResultState.SUCCESS_WITH_WARNINGS)
        if not model_validity:
            notes.append(f"[model] status={sim_result.status.value}")

        numerical_convergence = sim_result.convergence == ConvergenceStatus.CONVERGED
        if not numerical_convergence:
            notes.append(f"[numerical] convergence={sim_result.convergence.value}")

        physical_constraints = "not_applicable"
        if constraints:
            statuses = [c.evaluate(sim_result.outputs) for c in constraints]
            if any(s == ConstraintStatus.VIOLATED for s in statuses):
                physical_constraints = "VIOLATED"
                violated_names = [
                    c.name for c, s in zip(constraints, statuses) if s == ConstraintStatus.VIOLATED
                ]
                notes.append(f"[constraints] violadas: {violated_names}")
            elif any(s == ConstraintStatus.UNKNOWN for s in statuses):
                physical_constraints = "UNKNOWN"
                notes.append("[constraints] al menos una constraint no pudo evaluarse (UNKNOWN != satisfecha)")
            else:
                physical_constraints = "SATISFIED"

        benchmark_comparison = None
        if benchmark_result is not None:
            benchmark_comparison = "PASSED" if benchmark_result.passed else "FAILED"
            if not benchmark_result.passed:
                notes.append(f"[benchmark] {benchmark_result.detail}")

        return ValidationReport(
            input_validity=input_validity,
            dimensional_consistency=dimensional_consistency,
            model_validity=model_validity,
            numerical_convergence=numerical_convergence,
            physical_constraints=physical_constraints,
            benchmark_comparison=benchmark_comparison,
            notes=notes,
        )
