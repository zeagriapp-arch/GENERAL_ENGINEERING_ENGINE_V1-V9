"""
Evaluación determinista de `Operator` (sección 3).

Contraste deliberado con `core.physics.schema.PhysicsConstraint.evaluate()`
(el resto del proyecto): esa clase guarda la relación como una expresión de
texto ("thrust >= 0.5") y la parsea con una regex en tiempo de evaluación.
Aquí el operador YA es un enum estructurado desde que se crea el
`RequirementCandidate` — no hay texto que parsear ni ambigüedad posible.
Esta es precisamente la mejora que pide la sección 3 sobre el patrón
existente, no una reimplementación arbitraria.
"""
from __future__ import annotations

from requirement_contract.schema import Operator, ScalarValue

DEFAULT_APPROX_RELATIVE_TOLERANCE = 1e-3


class OperatorEvaluationError(ValueError):
    pass


_COMPARISON_OPERATORS = {Operator.EQ, Operator.NEQ, Operator.LT, Operator.LTE, Operator.GT, Operator.GTE, Operator.APPROX}
_MEMBERSHIP_OPERATORS = {Operator.IN, Operator.NOT_IN}


def evaluate(
    operator: Operator,
    actual: ScalarValue,
    target: ScalarValue | list[ScalarValue],
    *,
    approx_relative_tolerance: float = DEFAULT_APPROX_RELATIVE_TOLERANCE,
) -> bool:
    """
    Evalúa `actual OPERATOR target`. Para IN/NOT_IN, `target` debe ser una
    lista; para el resto, un escalar. Lanza `OperatorEvaluationError` si la
    combinación operador/tipo de dato no es evaluable (nunca devuelve un
    booleano inventado ante datos incoherentes).
    """
    if operator in _MEMBERSHIP_OPERATORS:
        if not isinstance(target, list):
            raise OperatorEvaluationError(f"Operador {operator.value} requiere 'target' como lista, recibido: {type(target).__name__}")
        is_member = actual in target
        return is_member if operator == Operator.IN else not is_member

    if operator not in _COMPARISON_OPERATORS:
        raise OperatorEvaluationError(f"Operador no reconocido: {operator!r}")

    if isinstance(target, list):
        raise OperatorEvaluationError(f"Operador {operator.value} no admite 'target' como lista.")

    if operator == Operator.APPROX:
        if not isinstance(actual, (int, float)) or not isinstance(target, (int, float)):
            raise OperatorEvaluationError("Operador APPROX requiere valores numéricos.")
        denom = abs(target) if target != 0 else 1.0
        return abs(actual - target) / denom <= approx_relative_tolerance

    if operator == Operator.EQ:
        return actual == target
    if operator == Operator.NEQ:
        return actual != target

    # LT/LTE/GT/GTE requieren orden total — solo numéricos (bool es subclase
    # de int en Python, se permite deliberadamente: BOOLEAN + EQ/NEQ es el
    # caso normal, pero no se prohíbe LT/GT sobre bool si alguien lo pide).
    if not isinstance(actual, (int, float)) or not isinstance(target, (int, float)):
        raise OperatorEvaluationError(f"Operador {operator.value} requiere valores numéricos, recibido: {actual!r} / {target!r}")

    if operator == Operator.LT:
        return actual < target
    if operator == Operator.LTE:
        return actual <= target
    if operator == Operator.GT:
        return actual > target
    if operator == Operator.GTE:
        return actual >= target

    raise OperatorEvaluationError(f"Operador no manejado: {operator!r}")  # pragma: no cover — exhaustivo arriba


# ---------------------------------------------------------------------------
# Representación como intervalo numérico (usado por ConflictValidator para
# detectar contradicciones entre Requirements sobre el mismo subject.parameter
# sin necesitar lógica ad-hoc por par de operadores).
# ---------------------------------------------------------------------------


def as_interval(operator: Operator, target: ScalarValue) -> tuple[float, float] | None:
    """
    Traduce un operador de comparación numérico + su valor a un intervalo
    cerrado/abierto aproximado en la recta real `[lo, hi]`, usado solo para
    detección de conflictos (nunca para evaluar el Requirement en sí).
    Devuelve None si el operador no es representable como intervalo
    (EQ/NEQ/IN/NOT_IN/APPROX sobre no-numéricos, etc.).
    """
    if not isinstance(target, (int, float)) or isinstance(target, bool):
        return None
    if operator == Operator.LTE or operator == Operator.LT:
        return (float("-inf"), float(target))
    if operator == Operator.GTE or operator == Operator.GT:
        return (float(target), float("inf"))
    if operator == Operator.EQ:
        return (float(target), float(target))
    return None
