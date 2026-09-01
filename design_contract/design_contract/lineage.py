"""
`DesignLineage` (sección 3): linaje de GENERACIÓN (qué Design produjo qué
otro Design mediante qué transformación) — distinto del linaje de VERSIÓN
(`Design.parent_design_id`, D001 v1 -> v2 -> v3, ver `versioning.py`).

Ejemplo de la especificación:

```
             Design A
             /      \\
            /        \\
       Design B    Design C
          |
       Design D
```

`Design A` es el ancestro común; `Design B`/`Design C` son su
"generación 1"; `Design D` es "generación 2". Esto prepara
posteriormente algoritmos evolutivos/búsqueda de diseños — no se
implementa ningún algoritmo evolutivo en esta fase, solo la
representación del grafo de generación.

Modelado sobre el mismo patrón que
`core.orchestrator.report._ancestry_chain` (v09_advanced_ai, para
Experiments) y `requirement_contract.versioning.version_chain_ids` (para
Requirements) — aquí generalizado a un grafo con múltiples hijos por nodo,
no solo una cadena lineal.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LineageEdge(BaseModel):
    parent_id: str
    child_id: str
    transformation: str = Field(description="Qué operación produjo el hijo — ej. 'mutation', 'crossover', 'optimization_step', 'manual_revision'.")
    metadata: dict = Field(default_factory=dict)


class DesignLineage(BaseModel):
    """Grafo de generación sobre un conjunto de Designs conocidos."""

    root_ids: list[str] = Field(default_factory=list, description="Designs sin parent de generación conocido.")
    edges: list[LineageEdge] = Field(default_factory=list)

    def children_of(self, design_id: str) -> list[str]:
        return [e.child_id for e in self.edges if e.parent_id == design_id]

    def parents_of(self, design_id: str) -> list[str]:
        return [e.parent_id for e in self.edges if e.child_id == design_id]

    def generation_of(self, design_id: str) -> Optional[int]:
        """
        Distancia (en aristas) desde la raíz más cercana — None si
        `design_id` no aparece en ningún edge ni root conocido.
        """
        if design_id in self.root_ids:
            return 0
        parents = self.parents_of(design_id)
        if not parents:
            return None
        parent_generations = [g for p in parents if (g := self.generation_of(p)) is not None]
        if not parent_generations:
            return None
        return min(parent_generations) + 1

    def transformation_history(self, design_id: str) -> list[LineageEdge]:
        """Cadena de transformaciones desde la raíz más cercana hasta `design_id`, en orden."""
        chain: list[LineageEdge] = []
        current = design_id
        seen: set[str] = set()
        while True:
            incoming = next((e for e in self.edges if e.child_id == current), None)
            if incoming is None or current in seen:
                break
            seen.add(current)
            chain.append(incoming)
            current = incoming.parent_id
        chain.reverse()
        return chain

    def record(self, *, parent_id: str, child_id: str, transformation: str, **metadata) -> "DesignLineage":
        """Devuelve un DesignLineage NUEVO con la arista añadida — nunca muta (mismo principio funcional del resto del proyecto)."""
        new_edges = list(self.edges) + [LineageEdge(parent_id=parent_id, child_id=child_id, transformation=transformation, metadata=metadata)]
        new_roots = list(self.root_ids)
        if parent_id not in {e.child_id for e in new_edges} and parent_id not in new_roots:
            new_roots.append(parent_id)
        return DesignLineage(root_ids=new_roots, edges=new_edges)
