"""
ConstraintValidator (sección 14, paso 3): coherencia interna del propio
Requirement como restricción de ingeniería — distinto de `SchemaValidator`
(forma type/operator/value) y de `ConflictValidator` (coherencia CONTRA
otros Requirements). Aquí se valida, por ejemplo, que `uncertainty` y
`validity` sean compatibles dimensionalmente con `value`, y que
`dependencies` no incluya al propio Requirement.
"""
from __future__ import annotations

from core.validation.dimensional_analysis import are_compatible

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import Requirement
from requirement_contract.validators.base import Severity, ValidationContext, ValidationResult, Validator


class ConstraintValidator(Validator):
    name = "constraint_validator"

    def validate(self, candidate: RequirementCandidate, *, context: ValidationContext) -> ValidationResult:
        issues = []

        if candidate.uncertainty.unit is not None and candidate.value_unit is not None:
            if not are_compatible(candidate.uncertainty.unit, candidate.value_unit):
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="uncertainty.unit",
                        message=(
                            f"uncertainty.unit='{candidate.uncertainty.unit}' no es dimensionalmente compatible "
                            f"con value_unit='{candidate.value_unit}'."
                        ),
                    )
                )

        for cond_name, cond in candidate.validity.conditions.items():
            if cond.unit is not None and candidate.value_unit is not None and cond_name.strip().lower() == candidate.parameter.strip().lower():
                # Solo si la condición de validez es sobre el MISMO parameter que el Requirement
                # (ej. validity de "temperature" en un Requirement sobre "temperature")
                # se exige compatibilidad — validity sobre otros ejes (ej. "pressure" en un
                # Requirement sobre "mass") es deliberadamente independiente.
                if not are_compatible(cond.unit, candidate.value_unit):
                    issues.append(
                        self._issue(
                            severity=Severity.ERROR,
                            field=f"validity.conditions.{cond_name}.unit",
                            message=(
                                f"validity.conditions['{cond_name}'].unit='{cond.unit}' no es compatible con "
                                f"value_unit='{candidate.value_unit}' del mismo parameter."
                            ),
                        )
                    )

        # sección 11: un Requirement no puede depender de sí mismo. En este
        # punto de la pipeline el candidate todavía no tiene id propio, así
        # que solo se puede detectar auto-referencia si el caller la incluyó
        # explícitamente vía metadata (uso interno de tests/integración).
        self_id_hint = candidate.metadata.get("_self_id_hint")
        if self_id_hint is not None and self_id_hint in candidate.dependencies:
            issues.append(
                self._issue(severity=Severity.ERROR, field="dependencies", message="Un Requirement no puede depender de sí mismo.")
            )

        if len(candidate.dependencies) != len(set(candidate.dependencies)):
            issues.append(
                self._issue(severity=Severity.WARNING, field="dependencies", message="'dependencies' contiene ids duplicados.")
            )

        if candidate.dependencies:
            known_ids = {r.id for r in context.known_requirements if isinstance(r, Requirement)}
            missing = [dep_id for dep_id in candidate.dependencies if dep_id not in known_ids]
            if missing:
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="dependencies",
                        message=f"Dependencias referenciadas que no existen entre los Requirements conocidos: {missing}.",
                        missing_ids=missing,
                    )
                )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
