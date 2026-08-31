"""
RequirementValidationPipeline (sección 14): el único camino sancionado de
`RequirementCandidate` a `Requirement`.

Orden fijo (sección 1 y 14):
    SchemaValidator -> UnitValidator -> DimensionalValidator ->
    ConstraintValidator -> ConflictValidator -> ProvenanceValidator ->
    Requirement

Principio (sección "PRINCIPIO ARQUITECTÓNICO FUNDAMENTAL"): el LLM NUNCA
tiene autoridad para producir un `Requirement` directamente. Esta función
es la ÚNICA que construye uno a partir de un candidato — no existe otro
constructor público pensado para ese uso (`Requirement(...)` sigue siendo
invocable directamente, como cualquier `BaseModel`, para tests/fixtures,
pero ningún código de este paquete lo hace fuera de aquí).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import (
    Requirement,
    RequirementStatus,
    Value,
    Verification,
    VerificationStatus,
    new_id,
    utcnow,
)
from requirement_contract.validators.base import ValidationContext, ValidationIssue, ValidationResult
from requirement_contract.validators.conflict_validator import ConflictValidator
from requirement_contract.validators.constraint_validator import ConstraintValidator
from requirement_contract.validators.dimensional_validator import DimensionalValidator
from requirement_contract.validators.provenance_validator import ProvenanceValidator
from requirement_contract.validators.schema_validator import SchemaValidator
from requirement_contract.validators.unit_validator import UnitValidator, normalize_value


class ValidationReport(BaseModel):
    subject: str
    parameter: str
    results: list[ValidationResult]
    overall_status: RequirementStatus

    @property
    def all_issues(self) -> list[ValidationIssue]:
        return [issue for result in self.results for issue in result.issues]

    @property
    def has_errors(self) -> bool:
        return any(r.has_errors for r in self.results)

    @property
    def is_valid(self) -> bool:
        return self.overall_status == RequirementStatus.VALIDATED


class RequirementValidationPipeline:
    """
    Instanciable con validadores custom (para tests) o con los 6
    validadores por defecto de la especificación.
    """

    def __init__(
        self,
        *,
        schema_validator: Optional[SchemaValidator] = None,
        unit_validator: Optional[UnitValidator] = None,
        dimensional_validator: Optional[DimensionalValidator] = None,
        constraint_validator: Optional[ConstraintValidator] = None,
        conflict_validator: Optional[ConflictValidator] = None,
        provenance_validator: Optional[ProvenanceValidator] = None,
    ):
        self.schema_validator = schema_validator or SchemaValidator()
        self.unit_validator = unit_validator or UnitValidator()
        self.dimensional_validator = dimensional_validator or DimensionalValidator()
        self.constraint_validator = constraint_validator or ConstraintValidator()
        self.conflict_validator = conflict_validator or ConflictValidator()
        self.provenance_validator = provenance_validator or ProvenanceValidator()

    def run(
        self, candidate: RequirementCandidate, *, known_requirements: Optional[list[Requirement]] = None
    ) -> tuple[Optional[Requirement], ValidationReport]:
        context = ValidationContext(known_requirements=known_requirements or [])
        results: list[ValidationResult] = []

        schema_result = self.schema_validator.validate(candidate, context=context)
        results.append(schema_result)

        if not schema_result.passed:
            # provenance es independiente de la forma de value/operator — se
            # corre igual para dar un reporte completo, pero unit/dimensional/
            # constraint/conflict dependen de datos que SchemaValidator ya
            # marcó como incoherentes, así que no tiene sentido evaluarlos.
            results.append(self.provenance_validator.validate(candidate, context=context))
            return None, self._report(candidate, results, RequirementStatus.INVALID)

        results.append(self.unit_validator.validate(candidate, context=context))
        results.append(self.dimensional_validator.validate(candidate, context=context))
        results.append(self.constraint_validator.validate(candidate, context=context))
        conflict_result = self.conflict_validator.validate(candidate, context=context)
        results.append(conflict_result)
        results.append(self.provenance_validator.validate(candidate, context=context))

        non_conflict_errors = any(r.has_errors for r in results if r is not conflict_result)
        if non_conflict_errors:
            return None, self._report(candidate, results, RequirementStatus.INVALID)

        if conflict_result.has_errors:
            requirement = self._build_requirement(candidate, status=RequirementStatus.CONFLICTING)
            return requirement, self._report(candidate, results, RequirementStatus.CONFLICTING)

        requirement = self._build_requirement(candidate, status=RequirementStatus.VALIDATED)
        return requirement, self._report(candidate, results, RequirementStatus.VALIDATED)

    def _report(self, candidate: RequirementCandidate, results: list[ValidationResult], status: RequirementStatus) -> ValidationReport:
        return ValidationReport(subject=candidate.subject, parameter=candidate.parameter, results=results, overall_status=status)

    def _build_requirement(self, candidate: RequirementCandidate, *, status: RequirementStatus) -> Requirement:
        normalized_value, normalized_unit, notes = normalize_value(candidate.value_original, candidate.value_unit)
        value = Value(
            original_value=candidate.value_original,
            original_unit=candidate.value_unit,
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
            conversion_notes=notes,
        )
        verification = Verification(
            status=VerificationStatus.VERIFIED if status == RequirementStatus.VALIDATED else VerificationStatus.NEEDS_REVIEW,
            verified_by="RequirementValidationPipeline",
            verified_at=utcnow(),
            notes=[] if status == RequirementStatus.VALIDATED else [f"status={status.value} tras la validation pipeline — requiere revisión."],
        )
        return Requirement(
            id=new_id(),
            subject=candidate.subject,
            parameter=candidate.parameter,
            type=candidate.type,
            operator=candidate.operator,
            value=value,
            priority=candidate.priority,
            provenance=candidate.provenance,
            confidence=candidate.confidence,
            verification=verification,
            uncertainty=candidate.uncertainty,
            validity=candidate.validity,
            dependencies=list(candidate.dependencies),
            status=status,
            metadata=dict(candidate.metadata),
        )


_default_pipeline = RequirementValidationPipeline()


def validate_candidate(
    candidate: RequirementCandidate, *, known_requirements: Optional[list[Requirement]] = None
) -> tuple[Optional[Requirement], ValidationReport]:
    """Atajo de conveniencia sobre una pipeline por defecto — ver `RequirementValidationPipeline.run()`."""
    return _default_pipeline.run(candidate, known_requirements=known_requirements)
