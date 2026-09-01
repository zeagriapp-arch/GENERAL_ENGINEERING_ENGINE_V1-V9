from __future__ import annotations

from requirement_contract.schema import Priority

from design_contract.constraints import DesignConstraint
from design_contract.design_space import DesignSpace, DesignSpaceStatus
from design_contract.objectives import DesignObjective, ObjectiveDirection
from design_contract.relations import DesignRelation
from design_contract.variables import DesignDomain, VariableRole
from tests.conftest import cylinder_design_space, make_design_provenance, make_provenance, make_variable


class TestValidDesignSpace:
    def test_minimal_valid_space(self, basic_design_space):
        assert len(basic_design_space.variables) == 4
        assert basic_design_space.status == DesignSpaceStatus.DRAFT

    def test_free_variables_filters_by_role(self, basic_design_space):
        assert set(basic_design_space.free_variables()) == {"diameter", "length", "thickness", "material"}

    def test_estimate_size_matches_expected_combinatorics(self):
        space = cylinder_design_space()
        # 3 continuas a resolución 10 (default) * 3 categorías = 3000
        assert space.estimate_size() == 10 * 10 * 10 * 3

    def test_requirement_ids_reference_without_duplicating(self):
        space = cylinder_design_space(requirement_ids=["R001", "R002"])
        assert space.requirement_ids == ["R001", "R002"]

    def test_consistent_space_has_no_errors(self, basic_design_space):
        assert basic_design_space.validate_internal_consistency() == []


class TestIncompleteDesignSpace:
    def test_derived_variable_without_relation_is_incomplete(self):
        variables = {
            "volume": make_variable("volume", role=VariableRole.DERIVED, domain=DesignDomain.continuous(0, 1e6), unit="m^3"),
        }
        space = DesignSpace(name="incomplete", variables=variables, provenance=make_design_provenance())
        errors = space.validate_internal_consistency()
        assert any("DERIVED" in e for e in errors)


class TestInconsistentDesignSpace:
    def test_relation_referencing_unknown_input_is_inconsistent(self):
        variables = {"radius": make_variable("radius", domain=DesignDomain.continuous(0.1, 0.5))}
        relation = DesignRelation(name="volume", inputs=["radius", "height"], output="volume", expression="radius * height", provenance=make_provenance())
        space = DesignSpace(name="inconsistent", variables=variables, relations=[relation], provenance=make_design_provenance())
        errors = space.validate_internal_consistency()
        assert any("height" in e for e in errors)

    def test_constraint_referencing_undeclared_variable_is_inconsistent(self):
        variables = {"radius": make_variable("radius", domain=DesignDomain.continuous(0.1, 0.5))}
        constraint = DesignConstraint(name="bad", expression="radius >= mystery_variable", provenance=make_design_provenance())
        space = DesignSpace(name="inconsistent", variables=variables, constraints=[constraint], provenance=make_design_provenance())
        errors = space.validate_internal_consistency()
        assert any("mystery_variable" in e for e in errors)


class TestObjectivesAndConstraintsLiveOnDesignSpace:
    def test_objectives_attach_to_space(self):
        space = cylinder_design_space(objectives=[DesignObjective(name="mass", direction=ObjectiveDirection.MINIMIZE, metric="mass")])
        assert len(space.objectives) == 1

    def test_constraints_attach_to_space(self):
        c = DesignConstraint(name="c1", expression="thickness >= 0.001", priority=Priority.HARD, provenance=make_design_provenance())
        space = cylinder_design_space(constraints=[c])
        assert space.constraints[0].name == "c1"
