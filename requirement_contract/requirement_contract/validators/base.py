"""
Tipos comunes de la validation pipeline (sección 14).

Deliberadamente NO devuelve `True`/`False` — cada validador produce un
`ValidationResult` estructurado (validator/status/severity/message/field/
details), igual en espíritu a `core.validation.schema.ValidationReport`
del resto del proyecto (que tampoco es un booleano simple). No se reutiliza
esa clase textualmente porque `ValidationReport` está diseñada para
resultados de SIMULACIÓN física (convergencia numérica, benchmarks) — un
concepto distinto a validar un `RequirementCandidate` — pero se sigue el
mismo principio de diseño a propósito.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ValidationIssue(BaseModel):
    validator: str
    severity: Severity
    message: str
    field: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    validator_name: str
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)


class ValidationContext(BaseModel):
    """
    Estado compartido entre validadores de una misma corrida de pipeline —
    ej. los Requirements ya conocidos, necesarios para ConflictValidator y
    para verificar dependencias. No persiste nada por sí mismo (eso queda
    fuera de alcance de esta fase, ver REQUIREMENT_CONTRACT.md).
    """

    model_config = {"arbitrary_types_allowed": True}

    known_requirements: list[Any] = Field(default_factory=list)  # list[Requirement], Any para evitar import circular


class Validator(ABC):
    name: str

    @abstractmethod
    def validate(self, candidate: Any, *, context: ValidationContext) -> ValidationResult: ...

    def _result(self, *, passed: bool, issues: Optional[list[ValidationIssue]] = None) -> ValidationResult:
        return ValidationResult(validator_name=self.name, passed=passed, issues=issues or [])

    def _issue(self, *, severity: Severity, message: str, field: Optional[str] = None, **details: Any) -> ValidationIssue:
        return ValidationIssue(validator=self.name, severity=severity, message=message, field=field, details=details)
