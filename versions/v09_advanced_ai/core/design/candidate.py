"""
Lógica compartida para construir y validar un Design candidato a partir
de un punto del Design Space. Usada por `DesignEngine` (Phase 4,
exploración) y `Optimizer` (Phase 5, búsqueda matemática) — ninguno de
los dos duplica esta lógica.
"""
from __future__ import annotations

from core.design.design_space import DesignSpace
from core.design.repository import create
from core.design.schema import Design
from core.experiments.schema import Results
from core.physics.schema import ConstraintKind, ConstraintStatus, PhysicsConstraint
from core.requirements.schema import Parameter, ParameterType, Requirements


def build_design(requirements: Requirements, design_space: DesignSpace, candidate_values: dict[str, float]) -> Design:
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


def check_design_space_constraints(design_space: DesignSpace, candidate_values: dict[str, float]) -> list[str]:
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


def evaluate_requirements(requirements: Requirements, results: Results) -> tuple[bool, list[str]]:
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
            # UNKNOWN nunca cuenta como satisfecho (sección 9) — si es
            # hard, no hay evidencia suficiente para aceptar el candidato.
            hard_violated = hard_violated or constraint.hard

    return (not hard_violated), reasons
