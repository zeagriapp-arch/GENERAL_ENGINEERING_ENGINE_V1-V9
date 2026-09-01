"""
`DesignVariable` / `DesignDomain` (secciones 8, 9).

Generaliza `core.design.design_space.DesignVariable` (v09_advanced_ai):
esa clase solo soporta bounds continuos (`lower_bound`/`upper_bound: float`).
Aquí `DesignDomain` es una unión discriminada que cubre CONTINUOUS,
INTEGER, DISCRETE, BOOLEAN y CATEGORICAL — necesario para representar
`material ∈ [A, B, C]` (categórico) o `number_of_components ∈ [1, 20]`
(entero), que la clase existente no puede expresar.

Reutiliza `requirement_contract.schema.Provenance`/`ProvenanceSource`
directamente para la procedencia de una variable — a diferencia del
`Design` en sí (sección 27, vocabulario procedimental, ver
`schema.DesignProvenance`), una variable de diseño y sus bounds son más
parecidos epistémicamente a un `Requirement` ("¿de dónde sabemos que el
diámetro debe estar en [0.1, 0.5] m?") que a "cómo se generó un diseño".
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from requirement_contract.schema import Provenance, ScalarValue

from design_contract.schema import new_id


class VariableRole(str, Enum):
    """Sección 8. Evita mezclar variables de diseño con condiciones de simulación."""

    DESIGN = "DESIGN"  # puede modificarse durante la búsqueda
    FIXED = "FIXED"  # permanece constante
    DERIVED = "DERIVED"  # se calcula a partir de otras (ver relations.py)
    CONTROL = "CONTROL"  # condición de operación controlable


class DesignDomainType(str, Enum):
    """Sección 9."""

    CONTINUOUS = "CONTINUOUS"
    INTEGER = "INTEGER"
    DISCRETE = "DISCRETE"
    BOOLEAN = "BOOLEAN"
    CATEGORICAL = "CATEGORICAL"


class DesignDomainError(ValueError):
    pass


class DesignDomain(BaseModel):
    """
    Un dominio no lleva su propia `unit` — `DesignVariable.unit` es la
    única fuente de verdad para evitar dos lugares que puedan quedar
    inconsistentes entre sí.
    """

    kind: DesignDomainType
    lower_bound: Optional[float] = None  # CONTINUOUS / INTEGER
    upper_bound: Optional[float] = None  # CONTINUOUS / INTEGER
    allowed_values: Optional[list[ScalarValue]] = None  # DISCRETE / CATEGORICAL

    @model_validator(mode="after")
    def _shape_matches_kind(self) -> "DesignDomain":
        if self.kind in (DesignDomainType.CONTINUOUS, DesignDomainType.INTEGER):
            if self.lower_bound is None or self.upper_bound is None:
                raise ValueError(f"DesignDomain {self.kind.value} requiere 'lower_bound' y 'upper_bound'.")
            if self.lower_bound > self.upper_bound:
                raise ValueError(f"DesignDomain {self.kind.value} inválido: lower_bound={self.lower_bound} > upper_bound={self.upper_bound}.")
        if self.kind in (DesignDomainType.DISCRETE, DesignDomainType.CATEGORICAL):
            if not self.allowed_values:
                raise ValueError(f"DesignDomain {self.kind.value} requiere 'allowed_values' no vacío.")
        if self.kind == DesignDomainType.BOOLEAN and self.allowed_values is None:
            # BOOLEAN es un caso especial de CATEGORICAL con valores fijos {True, False} —
            # se autocompleta si el caller no lo especifica.
            self.allowed_values = [True, False]
        return self

    def contains(self, value: ScalarValue) -> bool:
        if self.kind in (DesignDomainType.CONTINUOUS, DesignDomainType.INTEGER):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False
            if self.kind == DesignDomainType.INTEGER and not float(value).is_integer():
                return False
            return self.lower_bound <= value <= self.upper_bound
        # DISCRETE / CATEGORICAL / BOOLEAN
        return value in (self.allowed_values or [])

    @classmethod
    def continuous(cls, lower: float, upper: float) -> "DesignDomain":
        return cls(kind=DesignDomainType.CONTINUOUS, lower_bound=lower, upper_bound=upper)

    @classmethod
    def integer(cls, lower: int, upper: int) -> "DesignDomain":
        return cls(kind=DesignDomainType.INTEGER, lower_bound=float(lower), upper_bound=float(upper))

    @classmethod
    def discrete(cls, values: list[ScalarValue]) -> "DesignDomain":
        return cls(kind=DesignDomainType.DISCRETE, allowed_values=list(values))

    @classmethod
    def categorical(cls, values: list[str]) -> "DesignDomain":
        return cls(kind=DesignDomainType.CATEGORICAL, allowed_values=list(values))

    @classmethod
    def boolean(cls) -> "DesignDomain":
        return cls(kind=DesignDomainType.BOOLEAN, allowed_values=[True, False])


class DesignVariable(BaseModel):
    """Sección 8. `type` (pedido explícitamente por la especificación) se expone
    como propiedad de solo lectura sobre `domain.kind` — evita que dos campos
    (`type` guardado + `domain.kind`) puedan quedar desincronizados."""

    id: str = Field(default_factory=new_id)
    name: str
    role: VariableRole = VariableRole.DESIGN
    domain: DesignDomain
    unit: Optional[str] = None
    provenance: Provenance

    @property
    def type(self) -> DesignDomainType:
        return self.domain.kind

    def contains(self, value: ScalarValue) -> bool:
        return self.domain.contains(value)
