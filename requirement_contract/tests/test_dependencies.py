from __future__ import annotations

from requirement_contract.graph import find_cycles, missing_dependencies
from requirement_contract.schema import Operator, Requirement, RequirementType, Value
from requirement_contract.validators.base import ValidationContext
from requirement_contract.validators.constraint_validator import ConstraintValidator
from requirement_contract.validators.pipeline import validate_candidate
from tests.conftest import make_candidate, make_provenance


def _locked_requirement(req_id: str, **overrides):
    """Requirement ya construido (no candidate) con id fijo, para armar grafos de prueba."""
    defaults = dict(
        id=req_id,
        subject="system",
        parameter="mass",
        type=RequirementType.LIMIT,
        operator=Operator.LTE,
        value=Value(original_value=20.0, original_unit="kg", normalized_value=20.0, normalized_unit="kg"),
        provenance=make_provenance(),
    )
    defaults.update(overrides)
    return Requirement(**defaults)


class TestValidDependency:
    def test_dependency_on_known_requirement_passes(self):
        r001 = _locked_requirement("R001")
        candidate = make_candidate(subject="system", parameter="propellant_mass", dependencies=["R001"])
        result = ConstraintValidator().validate(candidate, context=ValidationContext(known_requirements=[r001]))
        assert result.passed

    def test_pipeline_accepts_candidate_with_known_dependency(self):
        r001 = _locked_requirement("R001")
        candidate = make_candidate(subject="system", parameter="propellant_mass", dependencies=["R001"])
        requirement, report = validate_candidate(candidate, known_requirements=[r001])
        assert report.is_valid
        assert requirement.dependencies == ["R001"]


class TestMissingDependency:
    def test_dependency_on_unknown_requirement_fails(self):
        candidate = make_candidate(dependencies=["R999-does-not-exist"])
        result = ConstraintValidator().validate(candidate, context=ValidationContext(known_requirements=[]))
        assert not result.passed
        assert any(i.field == "dependencies" for i in result.issues)

    def test_missing_dependencies_helper(self):
        r001 = _locked_requirement("R001", dependencies=["R002"])
        assert missing_dependencies(r001, known_ids={"R001"}) == ["R002"]
        assert missing_dependencies(r001, known_ids={"R001", "R002"}) == []


class TestCircularDependency:
    def test_two_node_cycle_is_detected(self):
        r001 = _locked_requirement("R001", dependencies=["R002"])
        r002 = _locked_requirement("R002", parameter="propellant_mass", dependencies=["R001"])
        cycles = find_cycles([r001, r002])
        assert len(cycles) >= 1
        assert set(cycles[0]) == {"R001", "R002"}

    def test_self_dependency_is_a_cycle(self):
        r001 = _locked_requirement("R001", dependencies=["R001"])
        cycles = find_cycles([r001])
        assert cycles == [["R001", "R001"]]

    def test_acyclic_graph_has_no_cycles(self):
        r001 = _locked_requirement("R001")
        r002 = _locked_requirement("R002", parameter="propellant_mass", dependencies=["R001"])
        r003 = _locked_requirement("R003", parameter="structure_mass", dependencies=["R001", "R002"])
        assert find_cycles([r001, r002, r003]) == []

    def test_three_node_cycle_is_detected(self):
        r001 = _locked_requirement("R001", dependencies=["R003"])
        r002 = _locked_requirement("R002", parameter="propellant_mass", dependencies=["R001"])
        r003 = _locked_requirement("R003", parameter="structure_mass", dependencies=["R002"])
        cycles = find_cycles([r001, r002, r003])
        assert len(cycles) >= 1
