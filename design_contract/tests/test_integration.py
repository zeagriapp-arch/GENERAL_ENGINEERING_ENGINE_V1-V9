from __future__ import annotations

import pytest
from core.design.schema import Design as CoreDesign

from design_contract.candidate import CandidateDesign
from design_contract.integration import DesignNotLockedError, to_core_design
from design_contract.validators.pipeline import DesignValidationPipeline
from design_contract.versioning import lock
from tests.conftest import cylinder_design_space, make_design_provenance


def _locked_design():
    space = cylinder_design_space()
    candidate = CandidateDesign(
        design_space_id=space.id,
        variable_values={"diameter": 0.3, "length": 0.5, "thickness": 0.005, "material": "A"},
        provenance=make_design_provenance(),
    )
    design, report = DesignValidationPipeline(space).run(candidate)
    assert report.is_valid
    return lock(design)


class TestToCoreDesign:
    def test_produces_a_valid_core_design(self):
        locked = _locked_design()
        core_design = to_core_design(locked, domain="generic.mechanics")
        assert isinstance(core_design, CoreDesign)
        assert core_design.domain == "generic.mechanics"
        assert core_design.parameters["diameter"].value == 0.3
        assert core_design.parameters["diameter"].unit == "m"

    def test_provenance_references_the_source_design_id(self):
        locked = _locked_design()
        core_design = to_core_design(locked, domain="generic.mechanics")
        assert locked.id in core_design.provenance

    def test_requires_locked_status(self):
        space = cylinder_design_space()
        candidate = CandidateDesign(
            design_space_id=space.id,
            variable_values={"diameter": 0.3, "length": 0.5, "thickness": 0.005, "material": "A"},
            provenance=make_design_provenance(),
        )
        design, report = DesignValidationPipeline(space).run(candidate)
        assert report.is_valid
        assert design.status.value != "LOCKED"
        with pytest.raises(DesignNotLockedError):
            to_core_design(design, domain="generic.mechanics")

    def test_categorical_value_translates_as_is(self):
        locked = _locked_design()
        core_design = to_core_design(locked, domain="generic.mechanics")
        assert core_design.parameters["material"].value == "A"
