from __future__ import annotations

from requirement_contract.schema import (
    Operator,
    Priority,
    ProvenanceSource,
    Requirement,
    RequirementStatus,
    RequirementType,
    Uncertainty,
    UncertaintyType,
    VerificationStatus,
)
from requirement_contract.validators.pipeline import RequirementValidationPipeline, validate_candidate
from requirement_contract.versioning import lock
from tests.conftest import make_candidate, make_provenance


class TestObjetivoFinalDeLaFase:
    """
    'El sistema no debe superar 20 kg' -> Requirement estructurado
    equivalente a mass <= 20 kg, con tipo/operador/unidad/prioridad/
    provenance/verification/uncertainty/validity/dependencies/version/status
    completos, sin que el LLM haya tenido autoridad para saltarse ninguna
    validación (viene de un RequirementCandidate, pasa por la pipeline).
    """

    def test_full_flow_candidate_to_locked_requirement(self):
        candidate = make_candidate(
            subject="system",
            parameter="mass",
            type=RequirementType.LIMIT,
            operator=Operator.LTE,
            value_original=20.0,
            value_unit="kg",
            priority=Priority.HARD,
            provenance=make_provenance(ProvenanceSource.USER, actor="ingeniero-sistemas"),
            source_text="El sistema no debe superar 20 kg",
        )

        requirement, report = validate_candidate(candidate)

        # Validation -> Normalized Requirement
        assert report.is_valid
        assert requirement.value.original_value == 20.0
        assert requirement.value.original_unit == "kg"
        assert requirement.value.normalized_value == 20.0
        assert requirement.value.normalized_unit == "kg"

        # -> Verified Requirement
        assert requirement.verification.status == VerificationStatus.VERIFIED
        assert requirement.status == RequirementStatus.VALIDATED

        # Todos los campos del contrato están presentes y coherentes:
        assert requirement.type == RequirementType.LIMIT
        assert requirement.operator == Operator.LTE
        assert requirement.priority == Priority.HARD
        assert requirement.provenance.source_type == ProvenanceSource.USER
        assert requirement.uncertainty.type == UncertaintyType.NONE
        assert requirement.validity.conditions == {}
        assert requirement.dependencies == []
        assert requirement.version == 1

        # -> Locked Requirement
        locked = lock(requirement)
        assert locked.status == RequirementStatus.LOCKED
        assert str(locked) == "system.mass <= 20.0 kg [HARD]"


class TestPipelineInvalidCases:
    def test_incompatible_operator_for_type_is_invalid(self):
        candidate = make_candidate(type=RequirementType.BOOLEAN, operator=Operator.LTE, value_original=True)
        requirement, report = validate_candidate(candidate)
        assert requirement is None
        assert report.overall_status == RequirementStatus.INVALID
        assert report.has_errors

    def test_dimensionally_incoherent_candidate_is_invalid(self):
        candidate = make_candidate(parameter="mass", value_unit="seconds", value_original=500.0)
        requirement, report = validate_candidate(candidate)
        assert requirement is None
        assert report.overall_status == RequirementStatus.INVALID

    def test_unknown_unit_candidate_is_invalid(self):
        candidate = make_candidate(value_unit="glorbins")
        requirement, report = validate_candidate(candidate)
        assert requirement is None
        assert report.overall_status == RequirementStatus.INVALID

    def test_invalid_provenance_is_invalid(self):
        from requirement_contract.schema import Provenance

        candidate = make_candidate(provenance=Provenance(source_type=ProvenanceSource.DOCUMENT))  # sin document_id
        requirement, report = validate_candidate(candidate)
        assert requirement is None
        assert report.overall_status == RequirementStatus.INVALID

    def test_report_lists_every_issue_field_required_by_spec(self):
        candidate = make_candidate(value_unit="glorbins")
        _, report = validate_candidate(candidate)
        issue = report.all_issues[0]
        assert issue.validator and issue.severity and issue.message  # validator/severity/message siempre presentes
        assert hasattr(issue, "field")
        assert hasattr(issue, "details")


class TestPipelineConflictingCase:
    def test_conflicting_candidate_returns_requirement_marked_conflicting_not_none(self):
        existing = make_candidate(parameter="mass", operator=Operator.LTE, value_original=20.0)
        r1, r1_report = validate_candidate(existing)
        assert r1_report.is_valid

        conflicting_candidate = make_candidate(parameter="mass", operator=Operator.GTE, value_original=30.0)
        r2, r2_report = validate_candidate(conflicting_candidate, known_requirements=[r1])

        assert r2 is not None
        assert r2.status == RequirementStatus.CONFLICTING
        assert r2_report.overall_status == RequirementStatus.CONFLICTING
        assert not r2_report.is_valid

    def test_conflicting_requirement_cannot_be_locked(self):
        from requirement_contract.versioning import RequirementLockError

        existing = make_candidate(parameter="mass", operator=Operator.LTE, value_original=20.0)
        r1, _ = validate_candidate(existing)
        conflicting_candidate = make_candidate(parameter="mass", operator=Operator.GTE, value_original=30.0)
        r2, _ = validate_candidate(conflicting_candidate, known_requirements=[r1])

        import pytest

        with pytest.raises(RequirementLockError):
            lock(r2)


class TestPipelineIsInjectable:
    def test_custom_validators_can_be_swapped_in(self):
        from requirement_contract.validators.base import ValidationContext, ValidationResult
        from requirement_contract.validators.schema_validator import SchemaValidator

        class AlwaysFailsSchemaValidator(SchemaValidator):
            def validate(self, candidate, *, context: ValidationContext) -> ValidationResult:
                return self._result(passed=False, issues=[self._issue(severity="ERROR", message="forced failure for test")])

        pipeline = RequirementValidationPipeline(schema_validator=AlwaysFailsSchemaValidator())
        candidate = make_candidate()
        requirement, report = pipeline.run(candidate)
        assert requirement is None
        assert report.overall_status == RequirementStatus.INVALID
