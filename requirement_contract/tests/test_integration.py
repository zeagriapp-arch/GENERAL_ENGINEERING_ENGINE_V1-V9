from __future__ import annotations

import pytest

from core.requirements.schema import Constraint as CoreConstraint
from core.requirements.schema import Parameter as CoreParameter

from requirement_contract.integration import (
    RequirementIntegrationError,
    RequirementNotLockedError,
    to_core_constraint,
    to_core_parameter,
)
from requirement_contract.schema import Operator, Priority
from requirement_contract.validators.pipeline import validate_candidate
from requirement_contract.versioning import lock
from tests.conftest import make_candidate


def _locked(*, known_requirements=None, **overrides):
    candidate = make_candidate(**overrides)
    requirement, report = validate_candidate(candidate, known_requirements=known_requirements)
    assert report.is_valid
    return lock(requirement)


class TestToCoreConstraint:
    def test_produces_a_valid_core_constraint(self):
        req = _locked(subject="system", parameter="mass", operator=Operator.LTE, value_original=20.0, priority=Priority.HARD)
        constraint = to_core_constraint(req)
        assert isinstance(constraint, CoreConstraint)
        assert constraint.expression == "mass <= 20.0"
        assert constraint.hard is True
        assert constraint.unit == "kg"

    def test_soft_priority_maps_to_hard_false(self):
        req = _locked(priority=Priority.SOFT)
        constraint = to_core_constraint(req)
        assert constraint.hard is False

    def test_requires_locked_status(self):
        candidate = make_candidate()
        requirement, report = validate_candidate(candidate)
        assert report.is_valid
        assert requirement.status.value == "VALIDATED"  # todavía no LOCKED
        with pytest.raises(RequirementNotLockedError):
            to_core_constraint(requirement)

    def test_membership_operator_not_translatable_to_constraint(self):
        req = _locked(type="DISCRETE", operator=Operator.IN, value_original=["N2", "He"], value_unit=None)
        with pytest.raises(RequirementIntegrationError):
            to_core_constraint(req)


class TestToCoreParameter:
    def test_produces_a_valid_core_parameter(self):
        req = _locked(subject="system", parameter="mass", value_original=20.0, value_unit="kg")
        param = to_core_parameter(req)
        assert isinstance(param, CoreParameter)
        assert param.name == "mass"
        assert param.value == 20.0
        assert param.unit == "kg"
        assert param.type.value == "fixed"

    def test_provenance_source_type_is_recorded_as_source(self):
        req = _locked()
        param = to_core_parameter(req)
        assert param.source == "USER"

    def test_dependencies_are_preserved(self):
        r001 = _locked(subject="system", parameter="mass", value_original=20.0)
        req = _locked(subject="system", parameter="propellant_mass", dependencies=[r001.id], known_requirements=[r001])
        param = to_core_parameter(req)
        assert param.dependencies == [r001.id]

    def test_requires_locked_status(self):
        candidate = make_candidate()
        requirement, report = validate_candidate(candidate)
        with pytest.raises(RequirementNotLockedError):
            to_core_parameter(requirement)
