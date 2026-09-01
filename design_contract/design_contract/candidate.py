"""
`CandidateDesign` (sección 19) — una propuesta, sin la autoridad de un
`Design`. Mismo principio que `RequirementCandidate`
(`requirement_contract`): sin `id`/`version`/`status`/lineage propios —
esos los asigna únicamente la validation pipeline al construir un
`Design`.

```
CandidateDesign -> Schema -> Structural -> Unit -> Constraint -> Feasibility -> Design
```
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from design_contract.schema import Architecture, Component, DesignProvenance, Geometry, Material


class CandidateDesign(BaseModel):
    design_space_id: str = Field(description="DesignSpace dentro del cual se propone este candidato.")
    variable_values: dict[str, Any] = Field(
        default_factory=dict, description="Valores propuestos para variables role=DESIGN/CONTROL — nunca para DERIVED (se calculan, no se proponen)."
    )
    name: str = ""
    description: str = ""
    architecture: Optional[Architecture] = None
    components: list[Component] = Field(default_factory=list)
    geometry: Optional[Geometry] = None
    materials: list[Material] = Field(default_factory=list)
    provenance: DesignProvenance
    source_text: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
