"""
Schema de `Design` — una solución concreta de ingeniería, independiente de
dominio (sección 1, 29 de la especificación de esta fase).

Relación con lo que YA existe en `versions/v09_advanced_ai/core/design/`
(reutilizado como referencia de diseño, no copiado — ver
DESIGN_DESIGNSPACE_IMPLEMENTATION_REPORT.md sección 1 para el detalle
completo de por qué):

`core.design.schema.Design` es la representación ya construida, probada
end-to-end con física real (155+ tests, cold-gas thruster) y cableada a
`DesignEngine`/`OptunaOptimizer` — pero es deliberadamente simple: un solo
dominio de variables (continuas), `geometry` como `dict` sin tipar,
`provenance` como `list[str]`, sin lineage de hijos, sin roles de
variable. Esta fase pide un contrato mucho más rico (roles, dominios
múltiples, lineage con hijos, geometría/materiales extensibles,
provenance estructurada). Igual que `Requirement` (fase anterior) no
reemplazó a `core.requirements.schema.Requirements` sino que se paró un
nivel "antes" en el pipeline, `design_contract.Design` no reemplaza a
`core.design.schema.Design` — es la capa de AUTORÍA/DESCUBRIMIENTO,
anterior a que un diseño entre al Simulation Engine. La traducción entre
ambos (cuando exista un caso de uso real) es responsabilidad de
`integration.py`, deliberadamente mínima y no conectada en esta fase.

Reutiliza directamente de `requirement_contract` (paquete hermano):
`Value` (todo dato numérico con unidad, original+normalizado),
`Uncertainty`, y el patrón de ids/timestamps/inmutabilidad funcional.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from requirement_contract.schema import Uncertainty, Value


def new_id() -> str:
    """Mismo esquema que requirement_contract.schema.new_id / core.design.schema — uuid4().hex[:12]."""
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Provenance de Design (sección 27) — vocabulario PROCEDIMENTAL (cómo se
# produjo el diseño), distinto del vocabulario EPISTÉMICO de
# `requirement_contract.schema.ProvenanceSource` (USER/DOCUMENT/COMPUTED/
# ASSUMPTION/SYSTEM, de dónde salió una AFIRMACIÓN). No son el mismo
# concepto — no tendría sentido, por ejemplo, "DOCUMENT" para un Design (un
# diseño no "viene de un documento" de la misma forma que un dato numérico),
# y sí tiene sentido "OPTIMIZED"/"LLM_PROPOSED", que no existen para
# Requirement. Se define un enum nuevo, deliberadamente, en vez de forzar
# uno de los dos vocabularios a cubrir ambos casos.
# ---------------------------------------------------------------------------


class DesignProvenanceSource(str, Enum):
    USER = "USER"
    GENERATED = "GENERATED"
    IMPORTED = "IMPORTED"
    DERIVED = "DERIVED"
    OPTIMIZED = "OPTIMIZED"
    LLM_PROPOSED = "LLM_PROPOSED"
    SYSTEM = "SYSTEM"


class DesignProvenance(BaseModel):
    """Estructurada — nunca solo texto libre (mismo principio que Requirement, sección 7 de la fase anterior)."""

    source_type: DesignProvenanceSource
    actor: Optional[str] = Field(default=None, description="Quién/qué lo originó: user id, generador, algoritmo de optimización.")
    generator_id: Optional[str] = Field(default=None, description="id del DesignGenerator que lo produjo, si source_type=GENERATED.")
    import_reference: Optional[str] = Field(default=None, description="Referencia externa (archivo/sistema), si source_type=IMPORTED.")
    derived_from: list[str] = Field(default_factory=list, description="ids de Design/dato de los que se derivó (DERIVED/OPTIMIZED).")
    llm_model: Optional[str] = Field(default=None, description="Rol/modelo que propuso, si source_type=LLM_PROPOSED (nunca acoplado a un proveedor concreto).")
    notes: Optional[str] = None
    recorded_at: datetime = Field(default_factory=utcnow)


class DesignStatus(str, Enum):
    """Sección 28 — compatible en estilo con `requirement_contract.schema.RequirementStatus`."""

    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    FEASIBLE = "FEASIBLE"
    LOCKED = "LOCKED"
    INVALID = "INVALID"
    REJECTED = "REJECTED"


VALID_DESIGN_STATUS_TRANSITIONS: dict[DesignStatus, set[DesignStatus]] = {
    DesignStatus.DRAFT: {DesignStatus.CANDIDATE, DesignStatus.INVALID},
    DesignStatus.CANDIDATE: {DesignStatus.VALIDATED, DesignStatus.INVALID, DesignStatus.REJECTED},
    DesignStatus.VALIDATED: {DesignStatus.FEASIBLE, DesignStatus.INVALID, DesignStatus.REJECTED},
    DesignStatus.FEASIBLE: {DesignStatus.LOCKED, DesignStatus.REJECTED},
    DesignStatus.LOCKED: set(),  # terminal — revise() crea una nueva versión
    DesignStatus.INVALID: set(),
    DesignStatus.REJECTED: set(),
}


class InvalidDesignStatusTransitionError(ValueError):
    pass


def transition_design_status(current: DesignStatus, target: DesignStatus) -> DesignStatus:
    if target not in VALID_DESIGN_STATUS_TRANSITIONS[current]:
        raise InvalidDesignStatusTransitionError(f"Transición de status inválida: {current} -> {target}")
    return target


# ---------------------------------------------------------------------------
# Geometry (sección 6) — extensible, NO reducido a length/width/height.
# ---------------------------------------------------------------------------


class GeometryRepresentationType(str, Enum):
    PARAMETRIC = "PARAMETRIC"
    ANALYTICAL = "ANALYTICAL"
    MESH = "MESH"
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"


class Geometry(BaseModel):
    """
    Abstracción capaz de recibir geometría de generadores paramétricos,
    modelos matemáticos, CAD, mesh generators, o archivos externos — sin
    implementar ninguno de ellos aquí (no es un CAD).
    """

    representation_type: GeometryRepresentationType
    parameters: dict[str, Any] = Field(default_factory=dict, description="Forma libre — depende de representation_type.")
    source: Optional[str] = Field(default=None, description="Herramienta/archivo/modelo que produjo esta geometría.")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Materials (sección 7) — general, NO exclusivamente aeroespacial.
# ---------------------------------------------------------------------------


class MaterialProperty(BaseModel):
    """
    Una propiedad física de un material (ej. 'yield_strength', 'density').
    La incertidumbre vive por propiedad, no por Material completo — dos
    propiedades del mismo material típicamente tienen incertidumbres muy
    distintas (ej. densidad bien conocida, resistencia a fatiga incierta).
    """

    value: Value
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)


class Material(BaseModel):
    """
    Representación general — las propiedades son un dict abierto
    (extensible), nunca una lista fija de campos aeroespaciales.
    """

    id: str = Field(default_factory=new_id)
    name: str
    properties: dict[str, MaterialProperty] = Field(default_factory=dict)
    source: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Component / Architecture (secciones 4, 5) — genéricos, nunca
# RocketEngine/SatelliteThruster/AircraftWing en el núcleo.
# ---------------------------------------------------------------------------


class Component(BaseModel):
    id: str = Field(default_factory=new_id)
    type: str = Field(description="Etiqueta genérica libre (ej. 'structural_member', 'actuator') — nunca un enum de dominio.")
    parameters: dict[str, Value] = Field(default_factory=dict)
    geometry: Optional[Geometry] = None
    material_id: Optional[str] = Field(default=None, description="Referencia a Design.materials[i].id.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComponentInterface(BaseModel):
    """Relación/acoplamiento entre dos componentes — mismo concepto que
    `core.design.schema.ComponentInterface`, redefinido aquí porque usa
    `Value` (requirement_contract) en vez de `core.requirements.schema.Parameter`."""

    from_component: str
    to_component: str
    kind: str = Field(description="Naturaleza genérica del acople (ej. 'structural', 'thermal', 'electrical', 'fluid').")
    parameters: dict[str, Value] = Field(default_factory=dict)


class Architecture(BaseModel):
    """
    Cómo están organizados los componentes de un Design — sin asumir
    dominio. `hierarchy` permite agrupar componentes en subsistemas
    (System -> Subsystem -> Component) de forma completamente libre.
    """

    component_ids: list[str] = Field(default_factory=list, description="ids de Design.components incluidos en esta arquitectura.")
    hierarchy: dict[str, list[str]] = Field(
        default_factory=dict, description="subsystem_id -> [component_id, ...] — agrupación libre, sin profundidad fija."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Design — la unidad central de esta fase.
# ---------------------------------------------------------------------------


class Design(BaseModel):
    """
    Sección 1. Una solución concreta dentro de un DesignSpace — "diameter
    = 0.237 m, length = 0.641 m, material = B" en el ejemplo de la
    especificación. Se construye SIEMPRE a través de la validation
    pipeline (`design_contract.validators.pipeline`) a partir de un
    `CandidateDesign` — nunca directamente por el LLM.
    """

    id: str = Field(default_factory=new_id)
    version: int = 1
    name: str
    description: str = ""
    parent_design_id: Optional[str] = Field(default=None, description="Linaje de VERSIÓN (D001 v1 -> v2) — distinto de DesignLineage (linaje de GENERACIÓN, ver lineage.py).")

    architecture: Architecture = Field(default_factory=Architecture)
    components: list[Component] = Field(default_factory=list)
    geometry: Optional[Geometry] = None
    materials: list[Material] = Field(default_factory=list)
    parameters: dict[str, Value] = Field(default_factory=dict, description="Valores fijos/resueltos del diseño.")
    variables: dict[str, Any] = Field(
        default_factory=dict, description="dict[str, design_contract.variables.DesignVariable] — Any para evitar import circular en este módulo."
    )
    derived_quantities: dict[str, Value] = Field(default_factory=dict, description="Calculadas vía DesignRelation — nunca tratadas como independientes.")
    interfaces: list[ComponentInterface] = Field(default_factory=list)
    operating_conditions: dict[str, Value] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[Any] = Field(default_factory=list, description="list[design_contract.constraints.DesignConstraint] — Any para evitar import circular en este módulo.")

    provenance: DesignProvenance
    status: DesignStatus = DesignStatus.DRAFT
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def component_by_id(self, component_id: str) -> Optional[Component]:
        return next((c for c in self.components if c.id == component_id), None)

    def material_by_id(self, material_id: str) -> Optional[Material]:
        return next((m for m in self.materials if m.id == material_id), None)
