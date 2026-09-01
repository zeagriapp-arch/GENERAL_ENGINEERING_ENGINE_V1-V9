"""
SchemaValidator (sección 19, paso 1): completitud estructural de un
CandidateDesign contra el DesignSpace que referencia — antes de tocar
dominios/unidades/constraints.
"""
from __future__ import annotations

from design_contract.candidate import CandidateDesign
from design_contract.design_space import DesignSpace
from design_contract.validators.base import DesignValidationContext, Severity, ValidationResult, Validator
from design_contract.variables import VariableRole


class SchemaValidator(Validator):
    name = "schema_validator"

    def __init__(self, design_space: DesignSpace):
        self._design_space = design_space

    def validate(self, candidate: CandidateDesign, *, context: DesignValidationContext) -> ValidationResult:
        issues = []
        space = self._design_space

        if candidate.design_space_id != space.id:
            issues.append(
                self._issue(
                    severity=Severity.ERROR,
                    field="design_space_id",
                    message=f"CandidateDesign referencia design_space_id='{candidate.design_space_id}', se esperaba '{space.id}'.",
                )
            )

        unknown = sorted(set(candidate.variable_values) - set(space.variables))
        if unknown:
            issues.append(
                self._issue(severity=Severity.ERROR, field="variable_values", message=f"Variables no declaradas en el DesignSpace: {unknown}")
            )

        for name, var in space.variables.items():
            if var.role == VariableRole.DESIGN and name not in candidate.variable_values:
                issues.append(
                    self._issue(severity=Severity.ERROR, field="variable_values", message=f"Falta valor para variable DESIGN obligatoria: '{name}'.")
                )
            if var.role == VariableRole.DERIVED and name in candidate.variable_values:
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="variable_values",
                        message=f"'{name}' es role=DERIVED — no debe proponerse directamente, se calcula vía DesignRelation.",
                    )
                )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
