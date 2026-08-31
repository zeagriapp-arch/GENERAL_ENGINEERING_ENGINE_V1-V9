"""
Requirement Contract Engine.

Contrato central del motor: transforma un `RequirementCandidate` (propuesto
por un LLM u otra fuente no confiable) en un `Requirement` formal, validado
y trazable, sin que el proponente tenga autoridad para saltarse ninguna
validación determinista.

Ver REQUIREMENT_CONTRACT.md (raíz del repositorio) para la documentación
completa. Este paquete es independiente de dominio: no contiene ninguna
noción de satélites, propulsión, CFD, FEA ni ningún otro dominio de
ingeniería concreto.

Depende de `core.validation.dimensional_analysis` de `versions/v09_advanced_ai`
(instalado como paquete separado, ver README.md de esta carpeta) para
reutilizar el sistema de unidades/análisis dimensional ya existente y
validado en la auditoría de 2026-08-30 — no se reimplementa aquí.
"""
from __future__ import annotations

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import (
    Confidence,
    ConfidenceLevel,
    Operator,
    Priority,
    Provenance,
    ProvenanceSource,
    Requirement,
    RequirementStatus,
    RequirementType,
    Uncertainty,
    UncertaintyType,
    Validity,
    ValidityRange,
    Value,
    Verification,
    VerificationStatus,
)
from requirement_contract.validators.pipeline import RequirementValidationPipeline, validate_candidate

__all__ = [
    "Requirement",
    "RequirementCandidate",
    "RequirementType",
    "RequirementStatus",
    "Operator",
    "Priority",
    "Value",
    "Provenance",
    "ProvenanceSource",
    "Confidence",
    "ConfidenceLevel",
    "Verification",
    "VerificationStatus",
    "Uncertainty",
    "UncertaintyType",
    "Validity",
    "ValidityRange",
    "RequirementValidationPipeline",
    "validate_candidate",
]
