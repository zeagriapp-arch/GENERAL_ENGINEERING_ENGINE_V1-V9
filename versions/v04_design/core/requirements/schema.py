"""
Schemas de Requirements Engine (sección 9 de la especificación).

Toda tarea en lenguaje natural se convierte en esta representación
estructurada ANTES de tocar Knowledge/Design/Simulation. Cada Parameter
lleva su unidad explícita para que el gate de Dimensional Analysis pueda
operar (sección 10).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ParameterType(str, Enum):
    FIXED = "fixed"
    FREE = "free"
    DERIVED = "derived"
    CONSTRAINED = "constrained"
    FORBIDDEN = "forbidden"


class Parameter(BaseModel):
    """
    Un parámetro con toda la metadata que pide la sección 9:
    name, value, unit, type, range, source, uncertainty, mutable/fixed,
    dependencies.
    """

    name: str
    value: float | int | str | None = None
    unit: Optional[str] = Field(
        default=None,
        description="Unidad en formato compatible con `pint` (ej. 'N', 'kg/s', 'Pa'). "
        "None significa explícitamente adimensional, no 'sin especificar'.",
    )
    type: ParameterType = ParameterType.FIXED
    range: Optional[tuple[float, float]] = None
    source: Optional[str] = None
    uncertainty: Optional[float] = None
    dependencies: list[str] = Field(default_factory=list)

    @field_validator("range")
    @classmethod
    def range_is_ordered(cls, v: Optional[tuple[float, float]]) -> Optional[tuple[float, float]]:
        if v is not None and v[0] > v[1]:
            raise ValueError(f"range inválido: mínimo {v[0]} > máximo {v[1]}")
        return v


class Objective(BaseModel):
    name: str
    direction: str = Field(description="'minimize' o 'maximize'")
    metric: str
    weight: float = 1.0

    @field_validator("direction")
    @classmethod
    def valid_direction(cls, v: str) -> str:
        if v not in ("minimize", "maximize"):
            raise ValueError("direction debe ser 'minimize' o 'maximize'")
        return v


class Constraint(BaseModel):
    name: str
    expression: str = Field(description="Expresión simbólica, ej. 'thrust >= 0.5'")
    unit: Optional[str] = None
    hard: bool = Field(default=True, description="Si es False, es una preferencia, no un hard constraint.")


class Requirements(BaseModel):
    """Salida estructurada del Requirements Engine (sección 9)."""

    problem: str
    objectives: list[Objective] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    variables: dict[str, Parameter] = Field(default_factory=dict)
    operating_conditions: dict[str, Parameter] = Field(default_factory=dict)
    validation_requirements: list[str] = Field(default_factory=list)
    domain: str = Field(description="Domain pack objetivo, ej. 'satellite.propulsion'")

    def free_variables(self) -> dict[str, Parameter]:
        return {k: v for k, v in self.variables.items() if v.type == ParameterType.FREE}

    def fixed_variables(self) -> dict[str, Parameter]:
        return {k: v for k, v in self.variables.items() if v.type == ParameterType.FIXED}
