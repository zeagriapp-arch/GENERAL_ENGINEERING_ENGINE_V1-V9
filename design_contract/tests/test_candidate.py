from __future__ import annotations

import pytest
from pydantic import ValidationError

from design_contract.candidate import CandidateDesign
from design_contract.schema import Design
from tests.conftest import cylinder_design_space, make_design_provenance


class TestCandidateIsLessAuthoritativeThanDesign:
    def test_candidate_has_no_id_field(self):
        assert "id" not in CandidateDesign.model_fields

    def test_candidate_has_no_status_field(self):
        assert "status" not in CandidateDesign.model_fields

    def test_candidate_has_no_version_field(self):
        assert "version" not in CandidateDesign.model_fields

    def test_design_has_all_of_those_fields(self):
        for field in ("id", "status", "version"):
            assert field in Design.model_fields


class TestCandidateSchemaValid:
    def test_minimal_valid_candidate(self):
        space = cylinder_design_space()
        c = CandidateDesign(design_space_id=space.id, variable_values={"diameter": 0.3}, provenance=make_design_provenance())
        assert c.design_space_id == space.id

    def test_missing_provenance_raises(self):
        space = cylinder_design_space()
        with pytest.raises(ValidationError):
            CandidateDesign(design_space_id=space.id, variable_values={})
