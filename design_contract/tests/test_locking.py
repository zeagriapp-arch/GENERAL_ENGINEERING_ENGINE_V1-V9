from __future__ import annotations

import pytest

from design_contract.candidate import CandidateDesign
from design_contract.schema import DesignStatus
from design_contract.validators.pipeline import DesignValidationPipeline
from design_contract.versioning import DesignLockError, lock, revise
from tests.conftest import cylinder_design_space, make_design_provenance


def _feasible_design():
    space = cylinder_design_space()
    candidate = CandidateDesign(
        design_space_id=space.id,
        variable_values={"diameter": 0.3, "length": 0.5, "thickness": 0.005, "material": "A"},
        provenance=make_design_provenance(),
    )
    design, report = DesignValidationPipeline(space).run(candidate)
    assert report.is_valid
    assert design.status == DesignStatus.FEASIBLE
    return design


class TestLockingFromFeasible:
    def test_lock_succeeds(self):
        d = _feasible_design()
        locked = lock(d)
        assert locked.status == DesignStatus.LOCKED

    def test_locking_does_not_mutate_original(self):
        d = _feasible_design()
        lock(d)
        assert d.status == DesignStatus.FEASIBLE


class TestCannotLockFromOtherStatuses:
    def test_cannot_lock_draft(self):
        d = _feasible_design()
        draft = d.model_copy(update={"status": DesignStatus.DRAFT})
        with pytest.raises(DesignLockError):
            lock(draft)

    def test_cannot_lock_already_locked(self):
        d = _feasible_design()
        locked_once = lock(d)
        with pytest.raises(DesignLockError):
            lock(locked_once)

    def test_cannot_lock_validated_only(self):
        d = _feasible_design()
        validated = d.model_copy(update={"status": DesignStatus.VALIDATED})
        with pytest.raises(DesignLockError):
            lock(validated)


class TestLockedDesignNotSilentlyModified:
    def test_modification_requires_revise_producing_new_version(self):
        d = _feasible_design()
        locked = lock(d)

        revised = revise(locked, {})
        assert revised.status == DesignStatus.DRAFT
        assert revised.parent_design_id == locked.id
        assert revised.id != locked.id

        assert locked.status == DesignStatus.LOCKED  # el LOCKED original, intacto
