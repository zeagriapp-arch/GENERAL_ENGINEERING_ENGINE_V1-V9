"""
Reutiliza directamente `Severity`/`ValidationIssue`/`ValidationResult`/
`Validator` de `requirement_contract.validators.base` — es infraestructura
genérica de "resultado de validación estructurado", no específica de
Requirements, exactamente el tipo de pieza que la sección 34 pide buscar
antes de reimplementar. Solo se define un `ValidationContext` propio,
porque el de `requirement_contract` está tipado específicamente para
`known_requirements` — forzar ese nombre para `known_designs` sería más
confuso que definir uno propio de una línea.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from requirement_contract.validators.base import Severity, ValidationIssue, ValidationResult, Validator

__all__ = ["Severity", "ValidationIssue", "ValidationResult", "Validator", "DesignValidationContext"]


class DesignValidationContext(BaseModel):
    """Estado compartido entre validadores de una misma corrida de pipeline."""

    model_config = {"arbitrary_types_allowed": True}

    known_designs: list[Any] = Field(default_factory=list)  # list[design_contract.schema.Design]
