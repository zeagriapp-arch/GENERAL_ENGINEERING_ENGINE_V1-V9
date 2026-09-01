"""
`DesignConstraint` (secciones 12, 13).

NO duplica `Requirement`: un `Requirement` es la fuente de verdad sobre
qué debe cumplir el SISTEMA completo (`mass <= 20 kg`); un `DesignConstraint`
es una restricción necesaria para definir o explorar correctamente el
ESPACIO de diseño (`thickness >= minimum_thickness(diameter)`,
`component_a_mass + component_b_mass <= total_mass`) — puede no tener
ninguna relación con un Requirement (es puramente geométrica/estructural
del propio DesignSpace), o puede derivar explícitamente de uno
(`requirement_id`, nunca duplicando su contenido, solo referenciándolo).

Reutiliza `requirement_contract.schema.Priority` (HARD/SOFT) directamente
— sección 13 pide explícitamente NO duplicar esa semántica.

La expresión se evalúa con el mismo DSL seguro de `relations.py` (mismo
principio de la sección 31: nunca `eval()` sobre texto no controlado).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from requirement_contract.schema import Priority

from design_contract.relations import evaluate_expression, validate_expression_structure
from design_contract.schema import DesignProvenance, new_id


class DesignConstraint(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    expression: str = Field(description="Expresión booleana del DSL seguro, ej. 'thickness >= minimum_thickness(diameter)'.")
    priority: Priority = Priority.HARD
    requirement_id: Optional[str] = Field(
        default=None, description="Referencia explícita cuando esta restricción deriva de un Requirement — nunca duplica su contenido."
    )
    provenance: DesignProvenance
    metadata: dict = Field(default_factory=dict)

    def evaluate(self, values: dict[str, float]) -> bool:
        result = evaluate_expression(self.expression, values)
        if not isinstance(result, bool):
            raise TypeError(f"DesignConstraint '{self.name}': la expresión no evaluó a un booleano (resultado: {result!r}).")
        return result


def validate_constraint_expression(expression: str, *, allowed_names: set[str]) -> list[str]:
    """Punto de entrada de validación estructural, reexportado para pipeline.py — ver relations.validate_expression_structure."""
    return validate_expression_structure(expression, allowed_names=allowed_names)
