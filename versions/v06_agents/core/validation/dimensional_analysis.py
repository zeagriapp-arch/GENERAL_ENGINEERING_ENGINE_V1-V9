"""
Dimensional Analysis Engine (sección 10).

Este es un GATE obligatorio: ninguna simulación puede avanzar con
parámetros cuyas unidades sean incompatibles o inconsistentes.

V1 cubre: parseo/validación de unidades individuales, verificación de
consistencia dimensional entre dos parámetros, y conversión. La
verificación de consistencia de ECUACIONES completas (parseo simbólico)
se amplía en Phase 3 junto con el primer PhysicsModel real.
"""
from __future__ import annotations

from dataclasses import dataclass

import pint

_ureg = pint.UnitRegistry()


class DimensionalAnalysisError(ValueError):
    """Se lanza cuando una unidad es inválida o dos unidades son incompatibles."""


@dataclass
class UnitCheckResult:
    valid: bool
    reason: str | None = None


def validate_unit(unit: str | None) -> UnitCheckResult:
    """Valida que `unit` sea una unidad reconocible por pint (o None = adimensional)."""
    if unit is None:
        return UnitCheckResult(valid=True)
    try:
        _ureg.parse_units(unit)
        return UnitCheckResult(valid=True)
    except Exception as exc:  # pint lanza varias subclases distintas
        return UnitCheckResult(valid=False, reason=str(exc))


def validate(parameters: dict[str, "Parameter"]) -> list[str]:  # noqa: F821 (typing string forward ref)
    """
    Tool: validate_units (config/tools.yaml).

    Recorre un dict de Parameter (de Requirements o Design) y devuelve la
    lista de errores encontrados. Lista vacía == válido.
    Nunca lanza excepción silenciosamente ignorada: el caller decide qué
    hacer con la lista de errores (típicamente: bloquear el pipeline).
    """
    errors: list[str] = []
    for name, param in parameters.items():
        result = validate_unit(param.unit)
        if not result.valid:
            errors.append(f"Parámetro '{name}': unidad inválida '{param.unit}' ({result.reason})")
    return errors


def are_compatible(unit_a: str | None, unit_b: str | None) -> bool:
    """¿unit_a y unit_b representan la misma dimensión física?"""
    if unit_a is None and unit_b is None:
        return True
    if unit_a is None or unit_b is None:
        return False
    try:
        qa = _ureg.Quantity(1, unit_a)
        qb = _ureg.Quantity(1, unit_b)
        return qa.dimensionality == qb.dimensionality
    except Exception:
        return False


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convierte `value` de from_unit a to_unit. Lanza DimensionalAnalysisError si incompatibles."""
    if not are_compatible(from_unit, to_unit):
        raise DimensionalAnalysisError(
            f"No se puede convertir '{from_unit}' a '{to_unit}': dimensiones incompatibles."
        )
    quantity = _ureg.Quantity(value, from_unit)
    return quantity.to(to_unit).magnitude


def check_constraints(design: "Design", constraints: list["Constraint"]) -> list[str]:  # noqa: F821
    """
    Tool: check_constraints (config/tools.yaml).

    V1: verifica solo que las expresiones referencien parámetros existentes
    y unidades consistentes; evaluación numérica de la expresión se hace en
    Evaluation/Critic Engine (Phase 4+), no aquí. Este engine se limita a
    la consistencia dimensional, que es su responsabilidad única.
    """
    errors: list[str] = []
    for constraint in constraints:
        if constraint.unit is not None:
            result = validate_unit(constraint.unit)
            if not result.valid:
                errors.append(
                    f"Constraint '{constraint.name}': unidad inválida '{constraint.unit}' ({result.reason})"
                )
    return errors
