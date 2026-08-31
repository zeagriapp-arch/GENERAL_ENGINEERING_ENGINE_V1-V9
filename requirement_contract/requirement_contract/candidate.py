"""
`RequirementCandidate` (sección 13): lo que un LLM (u otra fuente no
determinista) puede proponer. Deliberadamente MENOS estricto que
`Requirement` — no tiene `id`/`version`/`status`/`verification` propios
(esos los asigna la pipeline al construir el `Requirement` final), y sus
campos numéricos no están todavía normalizados ni validados
dimensionalmente.

Un `RequirementCandidate` nunca tiene la autoridad de un `Requirement` —
no se guarda, no se referencia como dependencia de otro Requirement, y no
participa en detección de conflictos hasta pasar por la pipeline completa
(`requirement_contract.validators.pipeline.validate_candidate`).

Sin acoplamiento a ningún proveedor de LLM concreto (sección 20): este
modelo es un `pydantic.BaseModel` normal, exactamente el tipo de objeto
que ya se pasa como `response_schema=` a
`core.models.interfaces.ModelProvider.complete()` en el resto del
proyecto (ver `agents/base.py:Agent.ask()`) — Ollama, u otro proveedor
futuro, solo necesitan producir un JSON que valide contra este schema.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from requirement_contract.schema import (
    Confidence,
    Operator,
    Priority,
    Provenance,
    RequirementType,
    ScalarValue,
    Uncertainty,
    Validity,
)


class RequirementCandidate(BaseModel):
    """Propuesta cruda, previa a cualquier validación determinista."""

    subject: str
    parameter: str
    type: RequirementType
    operator: Operator

    value_original: Union[ScalarValue, list[ScalarValue], None] = Field(
        description="Valor tal como lo propone la fuente, sin normalizar todavía."
    )
    value_unit: Optional[str] = Field(default=None, description="Unidad propuesta por la fuente, sin validar todavía.")

    priority: Priority = Priority.SOFT
    provenance: Provenance
    confidence: Confidence = Field(default_factory=Confidence)
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)
    validity: Validity = Field(default_factory=Validity)
    dependencies: list[str] = Field(default_factory=list)

    source_text: Optional[str] = Field(
        default=None, description="Fragmento de lenguaje natural original, si existe (ej. 'El sistema no debe superar 20 kg')."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
