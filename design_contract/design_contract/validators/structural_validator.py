"""StructuralValidator (sección 19, paso 2): cada valor propuesto respeta el DesignDomain de su variable."""
from __future__ import annotations

from design_contract.candidate import CandidateDesign
from design_contract.design_space import DesignSpace
from design_contract.validators.base import DesignValidationContext, Severity, ValidationResult, Validator


class StructuralValidator(Validator):
    name = "structural_validator"

    def __init__(self, design_space: DesignSpace):
        self._design_space = design_space

    def validate(self, candidate: CandidateDesign, *, context: DesignValidationContext) -> ValidationResult:
        issues = []
        for name, value in candidate.variable_values.items():
            var = self._design_space.variables.get(name)
            if var is None:
                continue  # ya reportado por SchemaValidator
            if not var.contains(value):
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field=f"variable_values.{name}",
                        message=f"Valor {value!r} fuera del dominio de '{name}' ({var.domain.kind.value}).",
                    )
                )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
