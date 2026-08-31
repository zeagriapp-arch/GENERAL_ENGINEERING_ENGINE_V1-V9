"""
Schema de `Requirement` — la unidad fundamental de una condición de
ingeniería, independiente de dominio.

Convenciones reutilizadas deliberadamente del resto del repositorio
(`versions/v09_advanced_ai`), para no duplicar ni divergir de patrones ya
auditados:

- Ids cortos vía `uuid.uuid4().hex[:12]`, igual que
  `core.design.schema.Design`/`core.experiments.schema.Experiment`.
- Timestamps `datetime.now(timezone.utc)`, igual que todo el resto del
  proyecto.
- `Requirement` es un `BaseModel` mutable normal, NO `frozen=True` — igual
  que `Design`/`Experiment`. La inmutabilidad de un Requirement LOCKED no
  se logra congelando la clase (eso divergiría de la convención existente),
  sino por disciplina funcional en `versioning.py` (ver ese módulo): nunca
  se muta un Requirement en el lugar, `revise()` siempre devuelve un objeto
  nuevo con id/version nuevos — exactamente el patrón de
  `core.design.repository.modify()`/`clone()`.
- Todo dato numérico con unidad reutiliza el mismo formato de unidad
  compatible con `pint` que ya usa `core.requirements.schema.Parameter` —
  la validación/():conversión real vive en
  `core.validation.dimensional_analysis` (reutilizada, no reimplementada;
  ver `requirement_contract/validators/unit_validator.py`).

Lo que NO se reutiliza y por qué:

- `core.requirements.schema.Parameter`/`Constraint` describen una variable
  o restricción ya *resuelta* dentro de un `Requirements` (el contenedor
  agregado de todo un problema, equivalente conceptual al
  `EngineeringProblem` de la fase). `Requirement` (singular, este módulo)
  es la unidad ANTERIOR en el pipeline: una condición individual, todavía
  candidata a venir de un LLM, con provenance/confidence/verification
  propios y versionado independiente. Ambos conceptos son complementarios,
  no duplicados — la traducción de uno a otro (cuando un Requirement queda
  LOCKED) es responsabilidad de `requirement_contract/integration.py`,
  deliberadamente mínima en esta fase (sección 19 de la especificación:
  no construir todavía el Design Engine).
- `core.requirements.schema.ParameterType` (FIXED/FREE/DERIVED/CONSTRAINED/
  FORBIDDEN) describe el ROL de una variable dentro de una optimización —
  un concepto ortogonal a `RequirementType` (la FORMA de una condición:
  LIMIT/TARGET/RANGE/...). No hay solapamiento real que reutilizar.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, model_validator

ScalarValue = Union[float, int, str, bool]
"""Un valor atómico que un Requirement puede comparar. Listas de estos
(para DISCRETE/RANGE, operator IN/NOT_IN) se representan como
`list[ScalarValue]` en `Value.original_value`/`normalized_value`."""


def new_id() -> str:
    """Mismo esquema de id que `core.design.schema`/`core.experiments.schema`."""
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums (sección 2, 3, 4, 7, 8, 9, 12)
# ---------------------------------------------------------------------------


class RequirementType(str, Enum):
    """Sección 2. La FORMA de la condición — no confundir con el operador."""

    LIMIT = "LIMIT"
    TARGET = "TARGET"
    RANGE = "RANGE"
    EQUALITY = "EQUALITY"
    INEQUALITY = "INEQUALITY"
    BOOLEAN = "BOOLEAN"
    DISCRETE = "DISCRETE"
    QUALITATIVE = "QUALITATIVE"


class Operator(str, Enum):
    """
    Sección 3. Representación determinista y estructurada — nunca texto
    natural ("menor que"). `ConstraintValidator` (sección 14) verifica que
    el operador sea coherente con el `RequirementType` declarado.
    """

    EQ = "="
    NEQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    IN = "IN"
    NOT_IN = "NOT_IN"
    APPROX = "APPROX"


class Priority(str, Enum):
    """Sección 4. HARD: puede rechazar una solución. SOFT: input al futuro optimizador."""

    HARD = "HARD"
    SOFT = "SOFT"


class ProvenanceSource(str, Enum):
    """Sección 7."""

    USER = "USER"
    DOCUMENT = "DOCUMENT"
    COMPUTED = "COMPUTED"
    ASSUMPTION = "ASSUMPTION"
    SYSTEM = "SYSTEM"


class ConfidenceLevel(str, Enum):
    """
    Sección 8. Deliberadamente separado de `VerificationStatus` — un LLM
    puede reportar HIGH confidence y estar equivocado; la verificación es
    un hecho determinista, la confianza es una opinión del proponente.
    """

    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VerificationStatus(str, Enum):
    """Sección 8. Resultado objetivo de la pipeline de validación, nunca del LLM."""

    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class UncertaintyType(str, Enum):
    """Sección 9."""

    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
    INTERVAL = "INTERVAL"
    PERCENTAGE = "PERCENTAGE"
    DISTRIBUTION = "DISTRIBUTION"


class RequirementStatus(str, Enum):
    """
    Sección 12. Transiciones controladas — ver `validators/pipeline.py` (que
    produce PARSED/NORMALIZED/VALIDATED/INVALID/CONFLICTING) y
    `versioning.py` (que produce LOCKED, y rechaza mutar un LOCKED en el
    lugar).
    """

    DRAFT = "DRAFT"
    PARSED = "PARSED"
    NORMALIZED = "NORMALIZED"
    VALIDATED = "VALIDATED"
    LOCKED = "LOCKED"
    INVALID = "INVALID"
    BLOCKED = "BLOCKED"
    CONFLICTING = "CONFLICTING"


# Transiciones válidas — mismo espíritu que
# `core.orchestrator.state_machine._VALID_TRANSITIONS`: explícito y
# verificado en código, no solo documentado.
VALID_STATUS_TRANSITIONS: dict[RequirementStatus, set[RequirementStatus]] = {
    RequirementStatus.DRAFT: {RequirementStatus.PARSED, RequirementStatus.INVALID},
    RequirementStatus.PARSED: {RequirementStatus.NORMALIZED, RequirementStatus.INVALID},
    RequirementStatus.NORMALIZED: {
        RequirementStatus.VALIDATED,
        RequirementStatus.INVALID,
        RequirementStatus.CONFLICTING,
        RequirementStatus.BLOCKED,
    },
    RequirementStatus.VALIDATED: {RequirementStatus.LOCKED, RequirementStatus.CONFLICTING, RequirementStatus.BLOCKED},
    RequirementStatus.LOCKED: set(),  # terminal — revise() crea una nueva versión, no transiciona esta
    RequirementStatus.INVALID: set(),  # terminal para esta versión — corregir = nueva versión (revise)
    RequirementStatus.BLOCKED: {RequirementStatus.NORMALIZED, RequirementStatus.VALIDATED},  # tras resolver lo que bloquea
    RequirementStatus.CONFLICTING: {RequirementStatus.NORMALIZED, RequirementStatus.VALIDATED},  # tras resolver el conflicto
}


class InvalidStatusTransitionError(ValueError):
    pass


def transition_status(current: RequirementStatus, target: RequirementStatus) -> RequirementStatus:
    if target not in VALID_STATUS_TRANSITIONS[current]:
        raise InvalidStatusTransitionError(f"Transición de status inválida: {current} -> {target}")
    return target


# ---------------------------------------------------------------------------
# Value objects (secciones 5, 7, 8, 9, 10)
# ---------------------------------------------------------------------------


class Value(BaseModel):
    """
    Sección 5. Preserva SIEMPRE original y normalizado — nunca se descarta
    el valor/unidad tal como lo propuso la fuente. `normalized_*` empieza
    en None: lo completa `UnitValidator` de forma determinista (sección 6),
    nunca el LLM ni ningún código que no sea ese validador.

    Para RANGE/DISCRETE (operator IN/NOT_IN), `original_value`/
    `normalized_value` son una lista de escalares en vez de un escalar
    único — un solo `Value` cubre ambos casos sin necesitar un tipo
    paralelo "ValueRange".
    """

    original_value: Union[ScalarValue, list[ScalarValue], None]
    original_unit: Optional[str] = Field(
        default=None, description="Unidad tal como la propuso la fuente, formato compatible con pint."
    )
    normalized_value: Union[ScalarValue, list[ScalarValue], None] = None
    normalized_unit: Optional[str] = Field(
        default=None, description="Unidad SI canónica tras `UnitValidator`. None hasta que se normalice."
    )
    conversion_notes: list[str] = Field(
        default_factory=list, description="Registro explícito de la conversión aplicada — nunca una conversión silenciosa."
    )

    @property
    def is_normalized(self) -> bool:
        return self.normalized_value is not None


class Provenance(BaseModel):
    """
    Sección 7. Procedencia estructurada — nunca solo texto libre. Cada
    `source_type` exige sus propios campos obligatorios (verificado por
    `ProvenanceValidator`, no aquí — ver nota de diseño en el docstring del
    módulo: la validación semántica vive en la pipeline, el schema solo
    declara la forma).
    """

    source_type: ProvenanceSource
    actor: Optional[str] = Field(default=None, description="Quién/qué originó el dato: user id, nombre de agente, componente.")
    document_id: Optional[str] = Field(default=None, description="Requerido si source_type=DOCUMENT.")
    document_location: Optional[str] = Field(default=None, description="Página/sección dentro del documento, si aplica.")
    derivation_id: Optional[str] = Field(default=None, description="Requerido si source_type=COMPUTED.")
    derived_from: list[str] = Field(
        default_factory=list, description="ids de Requirement/dato usados para computar este valor (source_type=COMPUTED)."
    )
    assumption_text: Optional[str] = Field(default=None, description="Requerido si source_type=ASSUMPTION.")
    notes: Optional[str] = None
    recorded_at: datetime = Field(default_factory=utcnow)


class Confidence(BaseModel):
    """
    Sección 8. Opinión del proponente (típicamente el LLM) sobre su propia
    propuesta. NUNCA se usa para decidir si un Requirement es válido —
    solo `Verification` (deterministic) decide eso.
    """

    level: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Opcional, informativo, reportado por la fuente.")
    rationale: Optional[str] = None


class Verification(BaseModel):
    """
    Sección 8. Hecho objetivo producido por la pipeline de validación
    (`requirement_contract.validators`) o por revisión humana explícita —
    nunca por la sola afirmación del LLM.
    """

    status: VerificationStatus = VerificationStatus.UNVERIFIED
    verified_by: Optional[str] = Field(default=None, description="Nombre del validador/componente/persona que verificó.")
    verified_at: Optional[datetime] = None
    notes: list[str] = Field(default_factory=list)


class Uncertainty(BaseModel):
    """
    Sección 9. Contrato suficiente para uso futuro (Monte Carlo, propagación
    de incertidumbre) — sin implementar ese motor todavía, según el alcance
    de esta fase.
    """

    type: UncertaintyType = UncertaintyType.NONE
    lower: Optional[float] = None
    upper: Optional[float] = None
    percentage: Optional[float] = Field(default=None, description="Ej. 5.0 significa ±5%.")
    distribution_name: Optional[str] = Field(default=None, description="Ej. 'normal', 'uniform' — sin motor de muestreo en esta fase.")
    distribution_params: dict[str, float] = Field(default_factory=dict)
    unit: Optional[str] = None

    @model_validator(mode="after")
    def _shape_matches_type(self) -> "Uncertainty":
        if self.type == UncertaintyType.INTERVAL and (self.lower is None or self.upper is None):
            raise ValueError("Uncertainty tipo INTERVAL requiere 'lower' y 'upper'.")
        if self.type == UncertaintyType.INTERVAL and self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError(f"Uncertainty INTERVAL inválido: lower={self.lower} > upper={self.upper}.")
        if self.type == UncertaintyType.PERCENTAGE and self.percentage is None:
            raise ValueError("Uncertainty tipo PERCENTAGE requiere 'percentage'.")
        if self.type == UncertaintyType.DISTRIBUTION and not self.distribution_name:
            raise ValueError("Uncertainty tipo DISTRIBUTION requiere 'distribution_name'.")
        return self


class ValidityRange(BaseModel):
    """Sección 10. Un único eje de validez (ej. 'temperature': 250-400 K)."""

    min: Optional[float] = None
    max: Optional[float] = None
    unit: Optional[str] = None

    @model_validator(mode="after")
    def _ordered(self) -> "ValidityRange":
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"ValidityRange inválido: min={self.min} > max={self.max}.")
        return self


class Validity(BaseModel):
    """
    Sección 10. Extensible y agnóstica de dominio: `conditions` es un dict
    abierto {nombre_de_condición: ValidityRange}, no una lista fija de
    campos aeroespaciales.
    """

    conditions: dict[str, ValidityRange] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Requirement (unidad central)
# ---------------------------------------------------------------------------


class Requirement(BaseModel):
    """
    Sección 1. La unidad fundamental de una condición de ingeniería. Se
    construye SIEMPRE a través de la validation pipeline
    (`requirement_contract.validators.pipeline.validate_candidate`) a
    partir de un `RequirementCandidate` — nunca directamente por el LLM.

    `subject` vs `parameter`: `subject` es la entidad/componente al que
    aplica la condición (ej. "system", "structure.wing", cualquier string
    definido por el caller — el motor no impone vocabulario de dominio);
    `parameter` es la magnitud medible restringida (ej. "mass", "thrust",
    "temperature"). "El sistema no debe superar 20 kg" ->
    subject="system", parameter="mass".
    """

    id: str = Field(default_factory=new_id)
    version: int = 1
    previous_version_id: Optional[str] = Field(
        default=None, description="id del Requirement del que esta versión desciende (ver versioning.py:revise())."
    )

    subject: str
    parameter: str
    type: RequirementType
    operator: Operator
    value: Value

    priority: Priority = Priority.SOFT
    provenance: Provenance
    confidence: Confidence = Field(default_factory=Confidence)
    verification: Verification = Field(default_factory=Verification)
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)
    validity: Validity = Field(default_factory=Validity)
    dependencies: list[str] = Field(default_factory=list, description="ids de otros Requirement de los que este depende.")

    status: RequirementStatus = RequirementStatus.DRAFT
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def qualified_name(self) -> str:
        """'system.mass' — usado por ConflictValidator para agrupar Requirements sobre la misma magnitud."""
        return f"{self.subject}.{self.parameter}"

    def __str__(self) -> str:  # legible en logs/tests, no reemplaza a model_dump()
        val = self.value.normalized_value if self.value.is_normalized else self.value.original_value
        unit = self.value.normalized_unit or self.value.original_unit or ""
        return f"{self.qualified_name()} {self.operator.value} {val}{(' ' + unit) if unit else ''} [{self.priority.value}]"
