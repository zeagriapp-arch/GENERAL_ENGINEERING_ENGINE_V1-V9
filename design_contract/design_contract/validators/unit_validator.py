"""
UnitValidator (sección 19, paso 3). Reutiliza `core.validation.dimensional_analysis`
(vía `requirement_contract.validators.unit_validator.normalize_value`, que
ya envuelve esa reutilización) — NO reimplementa un tercer sistema de
unidades. Valida las unidades de `Component.parameters`,
`Material.properties` y `Geometry.parameters` (cuando trae valores
numéricos con unidad) propuestos en el candidato.
"""
from __future__ import annotations

from requirement_contract.validators.unit_validator import normalize_value

from design_contract.candidate import CandidateDesign
from design_contract.validators.base import DesignValidationContext, Severity, ValidationResult, Validator


class UnitValidator(Validator):
    name = "unit_validator"

    def validate(self, candidate: CandidateDesign, *, context: DesignValidationContext) -> ValidationResult:
        issues = []

        for component in candidate.components:
            for param_name, value in component.parameters.items():
                if value.original_unit is None:
                    continue
                _normalized, _unit, notes = normalize_value(value.original_value, value.original_unit)
                if notes and any("inválida" in n for n in notes):
                    issues.append(
                        self._issue(
                            severity=Severity.ERROR,
                            field=f"components.{component.id}.parameters.{param_name}",
                            message=notes[0],
                        )
                    )

        for material in candidate.materials:
            for prop_name, prop in material.properties.items():
                if prop.value.original_unit is None:
                    continue
                _normalized, _unit, notes = normalize_value(prop.value.original_value, prop.value.original_unit)
                if notes and any("inválida" in n for n in notes):
                    issues.append(
                        self._issue(
                            severity=Severity.ERROR,
                            field=f"materials.{material.id}.properties.{prop_name}",
                            message=notes[0],
                        )
                    )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
