"""
Design Space (Phase 4): el sistema debe saber explícitamente qué puede
modificar y dentro de qué límites — "así el sistema no genera miles de
diseños absurdos".

Se construye a partir de `Requirements` (Phase 1): las variables FREE se
convierten en `DesignVariable` explorables; las FIXED (+
operating_conditions) quedan como parámetros fijos del espacio.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from core.requirements.schema import Parameter, ParameterType, Requirements


class DesignVariable(BaseModel):
    """
    Una dimensión explorable del Design Space. `constraint` y
    `manufacturing_constraint` son expresiones simples tipo
    'variable OP literal_o_otra_variable' (misma sintaxis que
    `core.physics.schema.PhysicsConstraint` — limitación conocida de V1,
    no soporta expresiones algebraicas complejas en el lado derecho).
    """

    name: str
    lower_bound: float
    upper_bound: float
    unit: Optional[str] = None
    constraint: Optional[str] = None
    manufacturing_constraint: Optional[str] = None
    source: Optional[str] = None

    def contains(self, value: float) -> bool:
        return self.lower_bound <= value <= self.upper_bound


class DesignSpaceError(ValueError):
    pass


class DesignSpace(BaseModel):
    domain: str
    variables: dict[str, DesignVariable] = Field(default_factory=dict)
    fixed_parameters: dict[str, Parameter] = Field(default_factory=dict)

    @classmethod
    def from_requirements(cls, requirements: Requirements) -> "DesignSpace":
        variables: dict[str, DesignVariable] = {}
        fixed: dict[str, Parameter] = {}

        for name, param in requirements.variables.items():
            if param.type == ParameterType.FREE:
                if param.range is None:
                    raise DesignSpaceError(
                        f"Variable libre '{name}' no tiene 'range' definido — "
                        f"el Design Space requiere bounds explícitos para explorarla."
                    )
                variables[name] = DesignVariable(
                    name=name,
                    lower_bound=param.range[0],
                    upper_bound=param.range[1],
                    unit=param.unit,
                    source=param.source,
                )
            else:
                fixed[name] = param

        fixed.update(requirements.operating_conditions)
        return cls(domain=requirements.domain, variables=variables, fixed_parameters=fixed)

    def all_values_with(self, candidate: dict[str, float]) -> dict[str, float]:
        """Combina fixed_parameters (numéricos) + un punto candidato, para evaluar constraints."""
        values = {
            name: p.value
            for name, p in self.fixed_parameters.items()
            if isinstance(p.value, (int, float))
        }
        values.update(candidate)
        return values
