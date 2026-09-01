from __future__ import annotations

import pytest

from design_contract.candidate import CandidateDesign
from design_contract.schema import DesignStatus
from design_contract.validators.pipeline import DesignValidationPipeline
from design_contract.versioning import DesignRevisionError, revise
from tests.conftest import cylinder_design_space, make_design_provenance


def _feasible_design(**value_overrides):
    space = cylinder_design_space()
    values = {"diameter": 0.3, "length": 0.5, "thickness": 0.005, "material": "A"}
    values.update(value_overrides)
    candidate = CandidateDesign(design_space_id=space.id, variable_values=values, provenance=make_design_provenance())
    design, report = DesignValidationPipeline(space).run(candidate)
    assert report.is_valid
    return design


class TestReviseCreatesNewVersionWithoutDestroyingThePrevious:
    def test_revise_returns_different_object(self):
        d1 = _feasible_design()
        d2 = revise(d1, {})
        assert d2.id != d1.id
        assert d2.version == d1.version + 1
        assert d2.parent_design_id == d1.id

    def test_original_never_mutated(self):
        d1 = _feasible_design()
        original_id, original_status = d1.id, d1.status
        revise(d1, {})
        assert d1.id == original_id
        assert d1.status == original_status

    def test_revision_resets_status_to_draft(self):
        d1 = _feasible_design()
        d2 = revise(d1, {})
        assert d2.status == DesignStatus.DRAFT

    def test_d001_v1_and_v2_both_remain_inspectable(self):
        """D001 v1 -> D001 v2 -> D001 v3, historial preservado."""
        d_v1 = _feasible_design()
        d_v2 = revise(d_v1, {})
        d_v3 = revise(d_v2, {})
        assert [d_v1.version, d_v2.version, d_v3.version] == [1, 2, 3]
        assert len({d_v1.id, d_v2.id, d_v3.id}) == 3  # tres objetos distintos

    def test_actual_content_change(self):
        d1 = _feasible_design()
        d2 = revise(d1, {"name": "revised-name", "description": "cambiado"})
        assert d1.name != "revised-name"
        assert d2.name == "revised-name"


class TestReviseErrorHandling:
    def test_invalid_content_raises_revision_error(self):
        d1 = _feasible_design()
        with pytest.raises(DesignRevisionError):
            revise(d1, {"status": "NOT_A_VALID_STATUS_BUT_IGNORED_ANYWAY", "geometry": "not-a-geometry-object"})

    def test_protected_fields_cannot_be_set_directly(self):
        d1 = _feasible_design()
        d2 = revise(d1, {"id": "hand-crafted", "status": DesignStatus.LOCKED})
        assert d2.id != "hand-crafted"
        assert d2.status == DesignStatus.DRAFT
