"""
Schemas ampliados de Physics Engine (Phase 3 extendida — secciones 4, 5,
8, 9 del documento de especificación de Phase 3).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VariableType(str, Enum):
    STATE = "STATE"
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    PARAMETER = "PARAMETER"
    CONTROL = "CONTROL"
    DERIVED = "DERIVED"
    DESIGN_VARIABLE = "DESIGN_VARIABLE"
    CONSTANT = "CONSTANT"


class Variable(BaseModel):
    """Sección 4. Distingue explícitamente quién puede tocar cada valor."""

    name: str
    symbol: str
    value: Optional[float] = None
    unit: Optional[str] = None
    type: VariableType
    domain: str
    bounds: Optional[tuple[float, float]] = None
    description: str = ""
    source: Optional[str] = None
    uncertainty: Optional[float] = None
    status: str = "unset"  # "unset" | "computed" | "provided" | "derived"


class Parameter(BaseModel):
    """
    Sección 5. NOTA: distinto de `core.requirements.schema.Parameter`
    (que es la versión ligera usada en Requirements/Design desde Phase
    1). Este es el Parameter "completo" del Physics Engine, con bounds y
    confidence explícitos. Los parámetros derivados conservan
    `derived_from` para no perder la relación con el original.
    """

    name: str
    value: float
    unit: Optional[str] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    nominal_value: Optional[float] = None
    uncertainty: Optional[float] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    mutable: bool = False
    description: str = ""
    derived_from: list[str] = Field(default_factory=list)


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Assumption(BaseModel):
    """Sección 8. Objeto explícito — el Critic Agent (Phase 6) podrá cuestionarlo."""

    description: str
    affected_model: str
    justification: str = ""
    source: Optional[str] = None
    validity_range: Optional[tuple[float, float]] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM


class ConstraintKind(str, Enum):
    EQUALITY = "equality"
    INEQUALITY = "inequality"
    BOUND = "bound"
    PHYSICAL = "physical"
    NUMERICAL = "numerical"
    OPERATING = "operating"


class ConstraintStatus(str, Enum):
    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    UNKNOWN = "UNKNOWN"


class PhysicsConstraint(BaseModel):
    """
    Sección 9. NUNCA asumir que UNKNOWN significa satisfecho — por eso
    `evaluate()` devuelve un status de 3 valores, no un bool.
    """

    name: str
    kind: ConstraintKind
    expression: str  # ej. "exit_mach >= 1.0"
    description: str = ""

    def evaluate(self, values: dict[str, float]) -> ConstraintStatus:
        """
        V1: evalúa expresiones de comparación simples ('a >= b', 'a <= b',
        'a == b', 'a > b', 'a < b') sobre `values`. Cualquier variable
        referenciada que falte en `values` -> UNKNOWN (nunca se asume
        satisfecho por falta de datos).
        """
        import re

        m = re.match(r"^\s*(\w+)\s*(>=|<=|==|>|<)\s*(-?[\w.]+)\s*$", self.expression)
        if not m:
            return ConstraintStatus.UNKNOWN
        lhs_name, op, rhs_raw = m.groups()
        if lhs_name not in values:
            return ConstraintStatus.UNKNOWN
        lhs = values[lhs_name]
        try:
            rhs = values[rhs_raw] if rhs_raw in values else float(rhs_raw)
        except ValueError:
            return ConstraintStatus.UNKNOWN

        ops = {
            ">=": lhs >= rhs,
            "<=": lhs <= rhs,
            "==": abs(lhs - rhs) < 1e-9,
            ">": lhs > rhs,
            "<": lhs < rhs,
        }
        return ConstraintStatus.SATISFIED if ops[op] else ConstraintStatus.VIOLATED
