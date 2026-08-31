"""
Interfaz mínima de integración con `core.requirements.schema`
(versions/v09_advanced_ai), tal como permite la excepción de la sección 19
de la especificación de esta fase ("la única excepción es crear interfaces
mínimas necesarias para que Requirement pueda integrarse limpiamente").

Deliberadamente NO se conecta a ningún pipeline vivo (Orchestrator,
DesignEngine, etc.) — son funciones puras, sin efectos secundarios,
pensadas para que una fase futura las use quirúrgicamente. Construir el
`EngineeringProblem`/agregador completo (que ensamblaría muchos
`Requirement` en un `core.requirements.schema.Requirements`) queda
explícitamente fuera de alcance de esta fase.

Solo opera sobre Requirements con `status=LOCKED` — un Requirement que
todavía puede cambiar de contenido (DRAFT/VALIDATED/etc.) no debería
traducirse a una representación que el resto del motor trata como
definitiva.
"""
from __future__ import annotations

from core.requirements.schema import Constraint as CoreConstraint
from core.requirements.schema import Parameter as CoreParameter
from core.requirements.schema import ParameterType as CoreParameterType

from requirement_contract.operators import Operator
from requirement_contract.schema import Requirement, RequirementStatus

_COMPARISON_SYMBOLS = {
    Operator.EQ: "==",
    Operator.NEQ: "!=",
    Operator.LT: "<",
    Operator.LTE: "<=",
    Operator.GT: ">",
    Operator.GTE: ">=",
}


class RequirementNotLockedError(ValueError):
    pass


class RequirementIntegrationError(ValueError):
    pass


def _require_locked(requirement: Requirement) -> None:
    if requirement.status != RequirementStatus.LOCKED:
        raise RequirementNotLockedError(
            f"Requirement {requirement.id} tiene status={requirement.status.value}; solo se integran "
            f"Requirements LOCKED (bloqueados tras pasar la validation pipeline)."
        )


def to_core_constraint(requirement: Requirement) -> CoreConstraint:
    """
    Traduce un Requirement de tipo comparación (LIMIT/INEQUALITY/EQUALITY)
    a `core.requirements.schema.Constraint` — la expresión de texto que
    consume `core.physics.schema.PhysicsConstraint.evaluate()`. La
    conversión de operador estructurado a símbolo de texto es
    intencionalmente el único punto donde se "aplana" el operador — el
    Requirement en sí nunca pierde su representación estructurada.
    """
    _require_locked(requirement)
    if requirement.operator not in _COMPARISON_SYMBOLS:
        raise RequirementIntegrationError(
            f"Operador {requirement.operator.value} no tiene traducción directa a Constraint "
            f"(solo comparaciones escalares =, !=, <, <=, >, >=)."
        )
    value = requirement.value.normalized_value if requirement.value.is_normalized else requirement.value.original_value
    if isinstance(value, list):
        raise RequirementIntegrationError("to_core_constraint no admite Requirements con valor tipo lista (RANGE/DISCRETE).")

    symbol = _COMPARISON_SYMBOLS[requirement.operator]
    expression = f"{requirement.parameter} {symbol} {value}"
    return CoreConstraint(
        name=f"{requirement.qualified_name()}:{requirement.id}",
        expression=expression,
        unit=requirement.value.normalized_unit or requirement.value.original_unit,
        hard=(requirement.priority.value == "HARD"),
    )


def to_core_parameter(requirement: Requirement) -> CoreParameter:
    """
    Traduce un Requirement escalar (cualquier tipo) a
    `core.requirements.schema.Parameter` — útil cuando el Requirement
    representa un valor fijo/objetivo más que una restricción de
    comparación (ej. TARGET). El `ParameterType` resultante es siempre
    `FIXED`: decidir si un parámetro debe ser `FREE`/`CONSTRAINED` es
    responsabilidad del Design Engine (fuera de alcance de esta fase).
    """
    _require_locked(requirement)
    value = requirement.value.normalized_value if requirement.value.is_normalized else requirement.value.original_value
    if isinstance(value, list):
        raise RequirementIntegrationError("to_core_parameter no admite Requirements con valor tipo lista (RANGE/DISCRETE).")

    uncertainty_value = None
    if requirement.uncertainty.type.value == "PERCENTAGE" and requirement.uncertainty.percentage is not None:
        uncertainty_value = requirement.uncertainty.percentage / 100.0

    return CoreParameter(
        name=requirement.parameter,
        value=value,
        unit=requirement.value.normalized_unit or requirement.value.original_unit,
        type=CoreParameterType.FIXED,
        source=requirement.provenance.source_type.value,
        uncertainty=uncertainty_value,
        dependencies=list(requirement.dependencies),
    )
