"""
Schemas de Knowledge Engine (sección 8).

Separa explícitamente: raw documents, chunks, extracted facts, equations,
sources — tal como pide la especificación. `Source` es la pieza clave de
provenance: TODA afirmación importante debe poder rastrearse hasta aquí.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class Source(BaseModel):
    """Sección 7: source, document, page/section, claim, date, metadata."""

    id: str = Field(default_factory=_new_id)
    title: str
    publisher: str
    url: Optional[str] = None
    page_or_section: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)


class RawDocument(BaseModel):
    """Un documento curado ingresado al Knowledge Engine."""

    id: str = Field(default_factory=_new_id)
    title: str
    source: Source
    summary: str = Field(description="Resumen en palabras propias, NUNCA copiado del original.")
    domain: str


class Chunk(BaseModel):
    """Unidad de texto indexada en el vector store, ligada a su documento."""

    id: str = Field(default_factory=_new_id)
    document_id: str
    text: str
    chunk_index: int


class Equation(BaseModel):
    """
    Ecuación con metadata completa (sección 8: equations, parameters,
    relationships). La expresión matemática en sí no es una obra
    protegida por copyright (es un hecho/ley física); lo que Claude NUNCA
    reproduce es la prosa explicativa original de la fuente.
    """

    id: str = Field(default_factory=_new_id)
    name: str
    expression: str = Field(description="Notación simbólica, ej. 'F = mdot*Ve + (pe - p0)*Ae'")
    variables: dict[str, str] = Field(description="símbolo -> descripción corta")
    units: dict[str, str] = Field(description="símbolo -> unidad pint-compatible")
    assumptions: list[str] = Field(default_factory=list)
    validity_range: dict[str, tuple[float, float]] = Field(default_factory=dict)
    source_id: str
    domain: str


class ExtractedFact(BaseModel):
    """Sección 7: claim, extracted_value, unit, confidence, date, source."""

    id: str = Field(default_factory=_new_id)
    document_id: str
    claim: str
    extracted_value: Optional[float | str] = None
    unit: Optional[str] = None
    confidence: float
    source_id: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """Salida de KnowledgeEngine.search(): chunk + score + provenance resuelta."""

    chunk: Chunk
    score: float
    source: Source
    document_title: str
