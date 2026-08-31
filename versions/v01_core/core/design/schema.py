"""
Design Representation (secciones 11 y 12).

Representación universal de un diseño de ingeniería, agnóstica de
dominio. `domains/*` NUNCA define su propio schema de Design paralelo —
extiende `parameters`/`metadata` con lo que necesite, pero la forma
general (components, geometry, materials, interfaces, constraints,
objectives) es siempre esta.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from core.requirements.schema import Constraint, Objective, Parameter


class Component(BaseModel):
    id: str
    name: str
    kind: str
    properties: dict[str, Parameter] = Field(default_factory=dict)


class MaterialRef(BaseModel):
    name: str
    properties: dict[str, Parameter] = Field(default_factory=dict)
    source: Optional[str] = None


class ComponentInterface(BaseModel):
    """Relación/acoplamiento entre dos componentes (ej. junta, flujo compartido)."""

    from_component: str
    to_component: str
    kind: str
    parameters: dict[str, Parameter] = Field(default_factory=dict)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class Design(BaseModel):
    id: str = Field(default_factory=_new_id)
    parent_id: Optional[str] = None
    domain: str
    components: list[Component] = Field(default_factory=list)
    geometry: Optional[dict[str, Any]] = None
    materials: list[MaterialRef] = Field(default_factory=list)
    parameters: dict[str, Parameter] = Field(default_factory=dict)
    interfaces: list[ComponentInterface] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    objectives: list[Objective] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def free_parameters(self) -> dict[str, Parameter]:
        return {k: p for k, p in self.parameters.items() if p.type.value == "free"}
