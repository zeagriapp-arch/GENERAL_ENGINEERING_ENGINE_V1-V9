from __future__ import annotations

from requirement_contract.schema import Operator, Priority, RequirementType, Value
from requirement_contract.validators.pipeline import validate_candidate
from tests.conftest import make_candidate


class TestHardPriority:
    def test_hard_requirement_builds_with_hard_priority(self):
        candidate = make_candidate(priority=Priority.HARD)
        requirement, report = validate_candidate(candidate)
        assert report.is_valid
        assert requirement.priority == Priority.HARD

    def test_hard_priority_survives_into_integration_constraint(self):
        from requirement_contract.integration import to_core_constraint
        from requirement_contract.versioning import lock
        from requirement_contract.schema import RequirementStatus

        candidate = make_candidate(priority=Priority.HARD)
        requirement, report = validate_candidate(candidate)
        locked = lock(requirement)
        assert locked.status == RequirementStatus.LOCKED
        constraint = to_core_constraint(locked)
        assert constraint.hard is True


class TestSoftPriority:
    def test_soft_requirement_builds_with_soft_priority(self):
        candidate = make_candidate(priority=Priority.SOFT)
        requirement, report = validate_candidate(candidate)
        assert report.is_valid
        assert requirement.priority == Priority.SOFT

    def test_soft_priority_survives_into_integration_constraint_as_non_hard(self):
        from requirement_contract.integration import to_core_constraint
        from requirement_contract.versioning import lock

        candidate = make_candidate(priority=Priority.SOFT)
        requirement, report = validate_candidate(candidate)
        locked = lock(requirement)
        constraint = to_core_constraint(locked)
        assert constraint.hard is False


class TestPriorityDefault:
    def test_default_priority_is_soft(self):
        # RequirementCandidate.priority default = SOFT (sección 4: SOFT es el default
        # razonable — un candidato no debería poder auto-declararse bloqueante
        # sin que quien lo construye lo pida explícitamente).
        from requirement_contract.candidate import RequirementCandidate

        assert RequirementCandidate.model_fields["priority"].default == Priority.SOFT
