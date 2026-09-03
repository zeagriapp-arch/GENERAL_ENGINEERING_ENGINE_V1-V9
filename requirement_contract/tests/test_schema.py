from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_contract.schema import (
    InvalidStatusTransitionError,
    Operator,
    Priority,
    Requirement,
    RequirementStatus,
    RequirementType,
    Value,
    transition_status,
)
from tests.conftest import make_provenance


def _requirement(**overrides) -> Requirement:
    defaults = dict(
        subject="system",
        parameter="mass",
        type=RequirementType.LIMIT,
        operator=Operator.LTE,
        value=Value(original_value=20.0, original_unit="kg"),
        priority=Priority.HARD,
        provenance=make_provenance(),
    )
    defaults.update(overrides)
    return Requirement(**defaults)


class TestRequirementValid:
    def test_minimal_valid_requirement(self):
        req = _requirement()
        assert req.subject == "system"
        assert req.parameter == "mass"
        assert req.status == RequirementStatus.DRAFT
        assert req.version == 1
        assert req.previous_version_id is None

    def test_id_is_generated_and_unique(self):
        a, b = _requirement(), _requirement()
        assert a.id != b.id
        assert len(a.id) == 12  # uuid4().hex[:12], mismo esquema que Design/Experiment

    def test_qualified_name(self):
        req = _requirement(subject="satellite", parameter="mass")
        assert req.qualified_name() == "satellite.mass"

    def test_str_representation_includes_operator_and_priority(self):
        req = _requirement()
        text = str(req)
        assert "mass" in text and "<=" in text and "HARD" in text


class TestRequirementInvalidFieldsMissing:
    def test_missing_subject_raises(self):
        with pytest.raises(ValidationError):
            Requirement(
                parameter="mass",
                type=RequirementType.LIMIT,
                operator=Operator.LTE,
                value=Value(original_value=20.0, original_unit="kg"),
                provenance=make_provenance(),
            )

    def test_missing_value_raises(self):
        with pytest.raises(ValidationError):
            Requirement(
                subject="system",
                parameter="mass",
                type=RequirementType.LIMIT,
                operator=Operator.LTE,
                provenance=make_provenance(),
            )

    def test_missing_provenance_raises(self):
        with pytest.raises(ValidationError):
            Requirement(
                subject="system",
                parameter="mass",
                type=RequirementType.LIMIT,
                operator=Operator.LTE,
                value=Value(original_value=20.0, original_unit="kg"),
            )


class TestRequirementInvalidTypes:
    def test_wrong_type_for_operator_field_raises(self):
        with pytest.raises(ValidationError):
            Requirement(
                subject="system",
                parameter="mass",
                type=RequirementType.LIMIT,
                operator="not-an-operator",
                value=Value(original_value=20.0, original_unit="kg"),
                provenance=make_provenance(),
            )

    def test_wrong_type_for_requirement_type_field_raises(self):
        with pytest.raises(ValidationError):
            Requirement(
                subject="system",
                parameter="mass",
                type="NOT_A_TYPE",
                operator=Operator.LTE,
                value=Value(original_value=20.0, original_unit="kg"),
                provenance=make_provenance(),
            )

    def test_negative_version_type_ok_but_semantically_should_stay_positive(self):
        # version es un int simple (sin constraint >=1 explícito en el schema);
        # el contrato de "siempre positivo" lo garantiza versioning.py, no el schema.
        req = _requirement(version=1)
        assert req.version == 1


class TestStatusTransitions:
    def test_draft_to_parsed_is_valid(self):
        assert transition_status(RequirementStatus.DRAFT, RequirementStatus.PARSED) == RequirementStatus.PARSED

    def test_draft_to_locked_is_invalid(self):
        with pytest.raises(InvalidStatusTransitionError):
            transition_status(RequirementStatus.DRAFT, RequirementStatus.LOCKED)

    def test_locked_has_no_outgoing_transitions(self):
        with pytest.raises(InvalidStatusTransitionError):
            transition_status(RequirementStatus.LOCKED, RequirementStatus.VALIDATED)

    def test_validated_to_locked_is_valid(self):
        assert transition_status(RequirementStatus.VALIDATED, RequirementStatus.LOCKED) == RequirementStatus.LOCKED
