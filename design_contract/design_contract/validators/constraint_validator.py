"""
ConstraintValidator (sección 19, pasos 4-5: "Constraint validation" +
"Feasibility"). En esta fase ambos pasos colapsan en una sola llamada
determinista (`StructuralFeasibilityChecker`) porque, sin simulación
física todavía (sección 20/35), "factible" y "satisface los
DesignConstraint conocidos" son la misma pregunta. Cuando exista
Simulation (fase futura), Feasibility se dividirá en un paso propio que sí
invoque un simulador — el pipeline ya está preparado para ese punto de
extensión (ver `pipeline.py`).

Violaciones HARD bloquean (`Severity.ERROR` -> Design INVALID); SOFT se
reportan como advertencia y no impiden construir el Design (coherente con
"un Requirement/Constraint SOFT puede usarse por el futuro optimizador",
sección 4 de la fase de Requirement).
"""
from __future__ import annotations

from requirement_contract.schema import Priority

from design_contract.candidate import CandidateDesign
from design_contract.design_space import DesignSpace
from design_contract.feasibility import FeasibilityReport, StructuralFeasibilityChecker
from design_contract.validators.base import DesignValidationContext, Severity, ValidationResult, Validator


class ConstraintValidator(Validator):
    name = "constraint_validator"

    def __init__(self, design_space: DesignSpace, *, checker: StructuralFeasibilityChecker | None = None):
        self._design_space = design_space
        self._checker = checker or StructuralFeasibilityChecker()

    def validate(self, candidate: CandidateDesign, *, context: DesignValidationContext) -> ValidationResult:
        report: FeasibilityReport = self._checker.check(candidate.variable_values, self._design_space)
        issues = []

        hard_constraint_ids = {c.id for c in self._design_space.constraints if c.priority == Priority.HARD}
        for constraint_id in report.violated_constraints:
            severity = Severity.ERROR if constraint_id in hard_constraint_ids else Severity.WARNING
            constraint = next((c for c in self._design_space.constraints if c.id == constraint_id), None)
            name = constraint.name if constraint else constraint_id
            issues.append(
                self._issue(
                    severity=severity,
                    field="variable_values",
                    message=f"DesignConstraint '{name}' no satisfecho.",
                    constraint_id=constraint_id,
                )
            )

        for domain_violation in report.violated_domains:
            issues.append(
                self._issue(severity=Severity.ERROR, field=f"variable_values.{domain_violation}", message=f"Fuera de dominio: '{domain_violation}'.")
            )

        for note in report.notes:
            issues.append(self._issue(severity=Severity.INFO, message=note))

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)

    def check_feasibility(self, candidate: CandidateDesign) -> FeasibilityReport:
        """Acceso directo al FeasibilityReport completo (para que `pipeline.py` decida VALIDATED vs FEASIBLE)."""
        return self._checker.check(candidate.variable_values, self._design_space)
