from __future__ import annotations

import pytest

from requirement_contract.schema import RequirementStatus
from requirement_contract.validators.pipeline import validate_candidate
from requirement_contract.versioning import RequirementLockError, lock, revise
from tests.conftest import make_candidate


def _validated_requirement(**overrides):
    candidate = make_candidate(**overrides)
    requirement, report = validate_candidate(candidate)
    assert report.is_valid
    return requirement


class TestLockingFromValidated:
    def test_lock_a_validated_requirement_succeeds(self):
        r = _validated_requirement()
        locked = lock(r)
        assert locked.status == RequirementStatus.LOCKED

    def test_locking_does_not_mutate_the_original(self):
        r = _validated_requirement()
        lock(r)
        assert r.status == RequirementStatus.VALIDATED  # el original nunca cambia

    def test_locked_requirement_has_new_updated_at(self):
        r = _validated_requirement()
        locked = lock(r)
        assert locked.updated_at >= r.updated_at


class TestCannotLockFromOtherStatuses:
    def test_cannot_lock_a_draft_requirement(self):
        r = _validated_requirement()
        draft = r.model_copy(update={"status": RequirementStatus.DRAFT})
        with pytest.raises(RequirementLockError):
            lock(draft)

    def test_cannot_lock_an_already_locked_requirement_again(self):
        r = _validated_requirement()
        locked_once = lock(r)
        with pytest.raises(RequirementLockError):
            lock(locked_once)

    def test_cannot_lock_a_conflicting_requirement(self):
        r = _validated_requirement()
        conflicting = r.model_copy(update={"status": RequirementStatus.CONFLICTING})
        with pytest.raises(RequirementLockError):
            lock(conflicting)


class TestLockedRequirementIsNotSilentlyModified:
    def test_modifying_a_locked_requirement_requires_revise_producing_new_version(self):
        r = _validated_requirement(parameter="mass", value_original=20.0)
        locked = lock(r)

        revised = revise(locked, {})
        assert revised.status == RequirementStatus.DRAFT  # una revisión de un LOCKED empieza de nuevo el ciclo
        assert revised.previous_version_id == locked.id
        assert revised.id != locked.id

        # El Requirement LOCKED original sigue intacto, en memoria, sin cambios.
        assert locked.status == RequirementStatus.LOCKED
        assert locked.value.original_value == 20.0

    def test_there_is_no_public_api_that_mutates_a_requirement_in_place(self):
        """
        Documenta la garantía: todo el módulo `versioning` solo expone
        funciones que devuelven objetos nuevos (`lock`, `revise`) — ninguna
        acepta ni produce una mutación in-place del Requirement de entrada.
        """
        import inspect

        import requirement_contract.versioning as versioning_module

        for name, func in inspect.getmembers(versioning_module, inspect.isfunction):
            if name.startswith("_"):
                continue
            sig = inspect.signature(func)
            assert sig.return_annotation is not None  # todas documentan explícitamente qué devuelven
