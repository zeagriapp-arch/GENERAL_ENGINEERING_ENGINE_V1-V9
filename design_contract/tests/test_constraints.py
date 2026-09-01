from __future__ import annotations

from requirement_contract.schema import Priority

from design_contract.constraints import DesignConstraint, validate_constraint_expression
from tests.conftest import make_design_provenance


def _constraint(**overrides) -> DesignConstraint:
    defaults = dict(name="min_thickness", expression="thickness >= 0.002", priority=Priority.HARD, provenance=make_design_provenance())
    defaults.update(overrides)
    return DesignConstraint(**defaults)


class TestValidConstraints:
    def test_satisfied_constraint_evaluates_true(self):
        c = _constraint()
        assert c.evaluate({"thickness": 0.005}) is True

    def test_violated_constraint_evaluates_false(self):
        c = _constraint()
        assert c.evaluate({"thickness": 0.001}) is False

    def test_multi_variable_constraint(self):
        c = _constraint(name="mass_budget", expression="component_a_mass + component_b_mass <= total_mass")
        assert c.evaluate({"component_a_mass": 5.0, "component_b_mass": 3.0, "total_mass": 10.0}) is True
        assert c.evaluate({"component_a_mass": 7.0, "component_b_mass": 5.0, "total_mass": 10.0}) is False


class TestPriority:
    def test_hard_priority(self):
        c = _constraint(priority=Priority.HARD)
        assert c.priority == Priority.HARD

    def test_soft_priority(self):
        c = _constraint(priority=Priority.SOFT)
        assert c.priority == Priority.SOFT

    def test_default_priority_is_hard_for_design_constraints(self):
        # A diferencia de RequirementCandidate (default SOFT), un DesignConstraint
        # sin prioridad explícita se asume HARD — es una restricción necesaria
        # para que el espacio de diseño tenga sentido, no una preferencia.
        from design_contract.constraints import DesignConstraint as DC

        assert DC.model_fields["priority"].default == Priority.HARD


class TestRequirementReference:
    def test_constraint_with_no_requirement_reference(self):
        c = _constraint()
        assert c.requirement_id is None

    def test_constraint_explicitly_deriving_from_a_requirement(self):
        c = _constraint(requirement_id="R001")
        assert c.requirement_id == "R001"

    def test_reference_never_duplicates_requirement_content(self):
        """Solo se guarda el id, nunca una copia de la expresión/valor del Requirement."""
        c = _constraint(requirement_id="R001")
        dumped = c.model_dump()
        assert dumped["requirement_id"] == "R001"
        assert "requirement" not in dumped  # no hay un campo que embeba el Requirement completo


class TestConstraintExpressionValidation:
    def test_valid_expression_structure(self):
        assert validate_constraint_expression("thickness >= 0.002", allowed_names={"thickness"}) == []

    def test_unsafe_expression_structure_rejected(self):
        errors = validate_constraint_expression("__import__('os')", allowed_names=set())
        assert errors
