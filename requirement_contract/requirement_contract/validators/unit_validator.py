"""
UnitValidator (sección 14, paso 2 / sección 5 y 6).

Reutiliza `core.validation.dimensional_analysis` de `versions/v09_advanced_ai`
tal cual — NO reimplementa parseo ni conversión de unidades (sección 6:
"si ya existe un sistema de unidades en el repositorio, reutilízalo").
`core` se resuelve en tiempo de ejecución al paquete `gede` (v09_advanced_ai)
instalado como dependencia editable — ver README.md de esta carpeta para
el setup.

Responsabilidad: (a) validar que `value_unit` sea una unidad reconocible
por pint, (b) producir el valor/unidad NORMALIZADOS de forma determinista
y explícita — nunca una conversión silenciosa (sección 5).

La normalización usa como unidad canónica la unidad base SI de la
dimensión detectada (vía `pint`), para que dos Requirements sobre el mismo
`parameter` en unidades distintas (ej. "20 lb" y "9 kg") terminen
comparables sin ambigüedad — necesario para que `ConflictValidator` pueda
comparar valores normalizados directamente.
"""
from __future__ import annotations

from typing import Optional

from core.validation.dimensional_analysis import convert, validate_unit

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import ScalarValue
from requirement_contract.validators.base import Severity, ValidationContext, ValidationResult, Validator


class UnitNormalizationError(ValueError):
    pass


def _si_base_unit(unit: str) -> str:
    """Unidad base SI de la misma dimensión que `unit`, vía pint (ej. 'lb' -> 'kg')."""
    import pint

    ureg = pint.UnitRegistry()
    quantity = ureg.Quantity(1, unit)
    return f"{quantity.to_base_units().units:~}"  # notación corta, ej. 'kg'


def normalize_value(
    value: ScalarValue | list[ScalarValue] | None, unit: Optional[str]
) -> tuple[ScalarValue | list[ScalarValue] | None, Optional[str], list[str]]:
    """
    Devuelve (valor_normalizado, unidad_normalizada, notas). Si `unit` es
    None (adimensional) o el valor no es numérico, no hay nada que
    convertir y se devuelve el valor tal cual, con una nota explícita.

    Nunca lanza una excepción por una unidad inválida/desconocida —
    `UnitValidator` es responsable de RECHAZAR esos candidatos (severity
    ERROR); esta función es una utilidad reutilizada también por
    `ConflictValidator`, que puede recibir un candidato que todavía no pasó
    por `UnitValidator`. Ante una unidad que `pint` no reconoce, devuelve
    el valor sin convertir con una nota explícita — nunca un resultado
    inventado, y nunca un crash no controlado.
    """
    if unit is None:
        return value, None, ["Sin unidad declarada — valor tratado como adimensional, sin conversión."]

    check = validate_unit(unit)
    if not check.valid:
        return value, unit, [f"No se pudo normalizar: unidad '{unit}' inválida ({check.reason}) — valor conservado sin convertir."]

    if isinstance(value, list):
        target_unit = _si_base_unit(unit)
        converted: list[ScalarValue] = []
        for v in value:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                converted.append(convert(float(v), unit, target_unit))
            else:
                converted.append(v)
        return converted, target_unit, [f"Lista convertida elemento a elemento de '{unit}' a '{target_unit}'."]

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        target_unit = _si_base_unit(unit)
        normalized = convert(float(value), unit, target_unit)
        return normalized, target_unit, [f"Convertido de '{value} {unit}' a '{normalized} {target_unit}' (unidad base SI)."]

    # Valor no numérico (str/bool) con unidad declarada: no hay conversión
    # posible — se conserva tal cual, se marca explícitamente.
    return value, unit, [f"Valor no numérico ({type(value).__name__}) con unidad '{unit}' declarada — no se aplica conversión."]


class UnitValidator(Validator):
    name = "unit_validator"

    def validate(self, candidate: RequirementCandidate, *, context: ValidationContext) -> ValidationResult:
        issues = []

        if candidate.value_unit is not None:
            check = validate_unit(candidate.value_unit)
            if not check.valid:
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="value_unit",
                        message=f"Unidad desconocida/inválida: '{candidate.value_unit}' ({check.reason})",
                    )
                )

        if candidate.uncertainty.unit is not None:
            check = validate_unit(candidate.uncertainty.unit)
            if not check.valid:
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="uncertainty.unit",
                        message=f"Unidad de incertidumbre desconocida/inválida: '{candidate.uncertainty.unit}' ({check.reason})",
                    )
                )

        for cond_name, cond in candidate.validity.conditions.items():
            if cond.unit is not None:
                check = validate_unit(cond.unit)
                if not check.valid:
                    issues.append(
                        self._issue(
                            severity=Severity.ERROR,
                            field=f"validity.conditions.{cond_name}.unit",
                            message=f"Unidad de validez desconocida/inválida: '{cond.unit}' ({check.reason})",
                        )
                    )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
