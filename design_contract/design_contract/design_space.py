"""
`DesignSpace` (sección 16): "¿qué soluciones podemos explorar?" — el
universo permitido de soluciones, matemáticamente. Distinto de
`SearchSpace` (`search_space.py`): la región que un algoritmo decide
explorar realmente (sección 17).

Generaliza `core.design.design_space.DesignSpace` (v09_advanced_ai): esa
clase solo tiene `variables: dict[str, DesignVariable]` (continuas) +
`fixed_parameters`, sin `relations`/`constraints`/`objectives` propios
(esos viven sueltos en `Requirements` en el sistema existente) ni
`status`/`provenance`. Aquí se consolidan todos los conceptos de la
sección 16 en un solo contrato explícito.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from design_contract.constraints import DesignConstraint
from design_contract.objectives import DesignObjective
from design_contract.relations import DesignRelation, validate_expression_structure
from design_contract.schema import DesignProvenance, new_id
from design_contract.variables import DesignVariable, VariableRole


class DesignSpaceStatus(str, Enum):
    """Compatible en estilo con RequirementStatus/DesignStatus."""

    DRAFT = "DRAFT"
    VALID = "VALID"
    INCOMPLETE = "INCOMPLETE"
    INCONSISTENT = "INCONSISTENT"


class DesignSpaceValidationError(ValueError):
    pass


class DesignSpace(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    variables: dict[str, DesignVariable] = Field(default_factory=dict)
    relations: list[DesignRelation] = Field(default_factory=list)
    constraints: list[DesignConstraint] = Field(default_factory=list)
    objectives: list[DesignObjective] = Field(default_factory=list)
    requirement_ids: list[str] = Field(
        default_factory=list, description="Requirements que este DesignSpace intenta satisfacer — referencia por id, nunca duplica su contenido (sección 30)."
    )
    provenance: DesignProvenance
    status: DesignSpaceStatus = DesignSpaceStatus.DRAFT
    metadata: dict = Field(default_factory=dict)

    def free_variables(self) -> dict[str, DesignVariable]:
        return {name: v for name, v in self.variables.items() if v.role == VariableRole.DESIGN}

    def fixed_variables(self) -> dict[str, DesignVariable]:
        return {name: v for name, v in self.variables.items() if v.role == VariableRole.FIXED}

    def derived_variable_names(self) -> set[str]:
        return {v.name for v in self.variables.values() if v.role == VariableRole.DERIVED}

    def relation_for_output(self, variable_name: str) -> Optional[DesignRelation]:
        return next((r for r in self.relations if r.output == variable_name), None)

    def estimate_size(self, *, continuous_resolution: int = 10) -> int:
        """
        Estimación aproximada de cardinalidad del DesignSpace completo
        (sección 17: "10^12 posibles combinaciones") — producto del número
        de valores considerados por cada variable DESIGN. CONTINUOUS se
        trata como discretizada a `continuous_resolution` puntos (un
        espacio continuo real es no numerable; esto es deliberadamente una
        estimación de orden de magnitud, no un conteo exacto).
        """
        from design_contract.variables import DesignDomainType

        total = 1
        for var in self.free_variables().values():
            domain = var.domain
            if domain.kind == DesignDomainType.CONTINUOUS:
                total *= continuous_resolution
            elif domain.kind == DesignDomainType.INTEGER:
                total *= int(domain.upper_bound - domain.lower_bound) + 1
            else:  # DISCRETE / CATEGORICAL / BOOLEAN
                total *= len(domain.allowed_values or [])
        return total

    def validate_internal_consistency(self) -> list[str]:
        """
        Chequeos deterministas baratos (sección 32: "espacio válido /
        incompleto / inconsistente"). No sustituye a
        `validators.pipeline` (que valida un CandidateDesign concreto) —
        esto valida la COHERENCIA del propio DesignSpace, útil antes de
        generar un solo candidato.
        """
        errors: list[str] = []

        derived_names = self.derived_variable_names()
        for name in derived_names:
            if self.relation_for_output(name) is None:
                errors.append(f"Variable '{name}' tiene role=DERIVED pero ningún DesignRelation la calcula.")

        known_names = set(self.variables.keys())
        for relation in self.relations:
            missing = sorted(set(relation.inputs) - known_names)
            if missing:
                errors.append(f"Relation '{relation.name}': inputs no encontrados en variables del DesignSpace: {missing}")
            if relation.output not in known_names:
                errors.append(f"Relation '{relation.name}': output '{relation.output}' no es una variable declarada del DesignSpace.")

        for constraint in self.constraints:
            struct_errors = validate_expression_structure(constraint.expression, allowed_names=known_names)
            errors.extend(f"Constraint '{constraint.name}': {e}" for e in struct_errors)

        return errors
