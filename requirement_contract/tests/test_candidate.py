from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import Operator, Requirement, RequirementType
from tests.conftest import make_candidate, make_provenance


class TestCandidateIsLessAuthoritativeThanRequirement:
    def test_candidate_has_no_id_field(self):
        assert "id" not in RequirementCandidate.model_fields

    def test_candidate_has_no_status_field(self):
        assert "status" not in RequirementCandidate.model_fields

    def test_candidate_has_no_version_field(self):
        assert "version" not in RequirementCandidate.model_fields

    def test_candidate_has_no_verification_field(self):
        """La verificación la asigna SIEMPRE la pipeline, nunca el proponente."""
        assert "verification" not in RequirementCandidate.model_fields

    def test_requirement_has_all_of_those_fields(self):
        for field in ("id", "status", "version", "verification"):
            assert field in Requirement.model_fields


class TestCandidateSchemaValid:
    def test_minimal_valid_candidate(self):
        c = make_candidate()
        assert c.subject == "system"
        assert c.operator == Operator.LTE

    def test_source_text_is_optional_free_text_hint(self):
        c = make_candidate(source_text="El sistema no debe superar 20 kg")
        assert c.source_text == "El sistema no debe superar 20 kg"


class TestCandidateSchemaInvalid:
    def test_missing_subject_raises(self):
        with pytest.raises(ValidationError):
            RequirementCandidate(
                parameter="mass",
                type=RequirementType.LIMIT,
                operator=Operator.LTE,
                value_original=20.0,
                value_unit="kg",
                provenance=make_provenance(),
            )

    def test_missing_provenance_raises(self):
        with pytest.raises(ValidationError):
            RequirementCandidate(
                subject="system",
                parameter="mass",
                type=RequirementType.LIMIT,
                operator=Operator.LTE,
                value_original=20.0,
                value_unit="kg",
            )

    def test_invalid_operator_type_raises(self):
        with pytest.raises(ValidationError):
            RequirementCandidate(
                subject="system",
                parameter="mass",
                type=RequirementType.LIMIT,
                operator=123,
                value_original=20.0,
                value_unit="kg",
                provenance=make_provenance(),
            )

    def test_value_original_field_is_required_but_accepts_none(self):
        # None es un valor explícito válido (ej. BOOLEAN/QUALITATIVE aún sin
        # resolver) — el campo debe estar presente, pero su ausencia total
        # sí debe fallar.
        with pytest.raises(ValidationError):
            RequirementCandidate(
                subject="system",
                parameter="mass",
                type=RequirementType.LIMIT,
                operator=Operator.LTE,
                value_unit="kg",
                provenance=make_provenance(),
            )
