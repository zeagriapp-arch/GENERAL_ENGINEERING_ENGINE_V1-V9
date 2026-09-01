"""
`DesignObjective` / `ObjectiveVector` (secciones 14, 15).

No reduce todo a un único score: `ObjectiveVector` preserva cada objetivo
por separado (performance, mass, cost, reliability, manufacturability,
novelty, ...) — la reducción a un solo número (si alguna vez hace falta)
es una decisión de una fase de Optimization futura, no de este contrato.
Sin optimizador Pareto todavía (sección 15 explícita) — solo el contrato.

Distinto de `core.requirements.schema.Objective` (v09_advanced_ai): ese
vive dentro de `Requirements` (el problema completo) y se usa para
alimentar `OptunaOptimizer` directamente. `DesignObjective` vive dentro de
`DesignSpace` (sección 16) — mismo concepto conceptual, nivel distinto del
pipeline, igual que `DesignConstraint` no duplica `Requirement`.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from design_contract.schema import new_id


class ObjectiveDirection(str, Enum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


class DesignObjective(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    direction: ObjectiveDirection
    metric: str = Field(description="Nombre de la variable/derived_quantity que este objetivo evalúa.")
    weight: Optional[float] = Field(default=None, description="Opcional — informativo hasta que exista un Optimization Engine que lo consuma.")
    priority: Optional[str] = Field(default=None, description="Etiqueta libre de prioridad relativa entre objetivos (ej. 'primary', 'secondary').")


class ObjectiveVector(BaseModel):
    """
    Vector de valores de objetivo para UN Design/CandidateDesign concreto —
    ej. [performance=0.82, mass=14.3, cost=1200, reliability=0.97]. Nunca
    colapsado a un único score dentro de este contrato.
    """

    values: dict[str, float] = Field(default_factory=dict, description="objective.name -> valor alcanzado.")

    def dominates(self, other: "ObjectiveVector", objectives: list[DesignObjective]) -> bool:
        """
        Dominancia de Pareto (sección 15: preparar el contrato, no
        implementar el optimizador) — al menos igual de bueno en todos los
        objetivos comparables y estrictamente mejor en al menos uno.
        Objetivos ausentes en cualquiera de los dos vectores se ignoran
        (no se puede comparar lo que no se midió).
        """
        comparable = [obj for obj in objectives if obj.metric in self.values and obj.metric in other.values]
        if not comparable:
            return False

        at_least_as_good_in_all = True
        strictly_better_in_one = False
        for obj in comparable:
            mine, theirs = self.values[obj.metric], other.values[obj.metric]
            better = mine > theirs if obj.direction == ObjectiveDirection.MAXIMIZE else mine < theirs
            worse = mine < theirs if obj.direction == ObjectiveDirection.MAXIMIZE else mine > theirs
            if worse:
                at_least_as_good_in_all = False
            if better:
                strictly_better_in_one = True
        return at_least_as_good_in_all and strictly_better_in_one
