from __future__ import annotations

import pytest

from requirement_contract.schema import RequirementStatus
from requirement_contract.validators.pipeline import validate_candidate
from requirement_contract.versioning import RequirementRevisionError, lock, revise, version_chain_ids
from tests.conftest import make_candidate


def _validated_requirement(**overrides):
    candidate = make_candidate(**overrides)
    requirement, report = validate_candidate(candidate)
    assert report.is_valid
    return requirement


class TestReviseCreatesNewVersionWithoutDestroyingThePrevious:
    def test_revise_returns_a_different_object(self):
        r1 = _validated_requirement(value_original=20.0)
        r2 = revise(r1, {})  # sin cambios de contenido reales, solo probar identidad
        assert r2.id != r1.id
        assert r2.version == r1.version + 1
        assert r2.previous_version_id == r1.id

    def test_original_object_is_never_mutated(self):
        r1 = _validated_requirement(value_original=20.0)
        original_id, original_status = r1.id, r1.status
        revise(r1, {})
        assert r1.id == original_id
        assert r1.status == original_status  # r1 sigue exactamente como estaba

    def test_revision_resets_status_to_draft_requiring_revalidation(self):
        r1 = _validated_requirement()
        assert r1.status == RequirementStatus.VALIDATED
        r2 = revise(r1, {})
        assert r2.status == RequirementStatus.DRAFT  # una revisión nunca hereda VALIDATED/LOCKED

    def test_r001_v1_and_r001_v2_both_remain_inspectable(self):
        """Ejemplo de la especificación: R001 v1 (mass<=20kg) -> R001 v2 (mass<=15kg), v1 se preserva."""
        r001_v1 = _validated_requirement(parameter="mass", value_original=20.0)
        r001_v2 = revise(r001_v1, {})
        # ambos objetos siguen siendo válidos e independientes en memoria
        assert r001_v1.version == 1
        assert r001_v2.version == 2
        assert r001_v1.id != r001_v2.id

    def test_actual_content_change_mass_20_to_15(self):
        """La revisión puede cambiar el valor real de la condición, no solo metadata."""
        r001_v1 = _validated_requirement(parameter="mass", value_original=20.0, value_unit="kg")
        new_value = r001_v1.value.model_copy(update={"original_value": 15.0, "normalized_value": None})
        r001_v2 = revise(r001_v1, {"value": new_value})

        assert r001_v1.value.original_value == 20.0  # v1 intacto
        assert r001_v2.value.original_value == 15.0  # v2 refleja el cambio
        assert r001_v2.previous_version_id == r001_v1.id


class TestVersionChain:
    def test_chain_reconstructs_ancestry_oldest_first(self):
        r1 = _validated_requirement()
        r2 = revise(r1, {})
        r3 = revise(r2, {})
        all_versions = {r1.id: r1, r2.id: r2, r3.id: r3}
        chain = version_chain_ids(r3, all_versions)
        assert chain == [r1.id, r2.id]

    def test_root_version_has_empty_chain(self):
        r1 = _validated_requirement()
        assert version_chain_ids(r1, {r1.id: r1}) == []


class TestReviseErrorHandling:
    def test_revise_with_invalid_content_raises_revision_error(self):
        r1 = _validated_requirement()
        with pytest.raises(RequirementRevisionError):
            revise(r1, {"type": "NOT_A_VALID_TYPE"})

    def test_revise_ignores_attempts_to_set_protected_fields_directly(self):
        r1 = _validated_requirement()
        r2 = revise(r1, {"id": "hand-crafted-id", "status": RequirementStatus.LOCKED})
        assert r2.id != "hand-crafted-id"
        assert r2.status == RequirementStatus.DRAFT
