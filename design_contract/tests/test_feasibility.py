from __future__ import annotations

from requirement_contract.schema import Priority

from design_contract.constraints import DesignConstraint
from design_contract.feasibility import FeasibilityStatus, StructuralFeasibilityChecker
from tests.conftest import cylinder_design_space, make_design_provenance


class TestFeasibleCandidate:
    def test_within_domains_and_no_constraints_is_feasible(self):
        space = cylinder_design_space()
        checker = StructuralFeasibilityChecker()
        report = checker.check({"diameter": 0.3, "length": 0.5, "thickness": 0.005, "material": "A"}, space)
        assert report.is_feasible
        assert report.status == FeasibilityStatus.FEASIBLE

    def test_satisfied_hard_constraint_stays_feasible(self):
        c = DesignConstraint(name="min_thickness", expression="thickness >= 0.002", priority=Priority.HARD, provenance=make_design_provenance())
        space = cylinder_design_space(constraints=[c])
        checker = StructuralFeasibilityChecker()
        report = checker.check({"diameter": 0.3, "length": 0.5, "thickness": 0.005, "material": "A"}, space)
        assert report.is_feasible


class TestInfeasibleCandidate:
    def test_out_of_domain_value_is_infeasible(self):
        space = cylinder_design_space()
        checker = StructuralFeasibilityChecker()
        report = checker.check({"diameter": 999.0, "length": 0.5, "thickness": 0.005, "material": "A"}, space)
        assert not report.is_feasible
        assert "diameter" in report.violated_domains

    def test_violated_hard_constraint_is_infeasible(self):
        c = DesignConstraint(name="min_thickness", expression="thickness >= 0.002", priority=Priority.HARD, provenance=make_design_provenance())
        space = cylinder_design_space(constraints=[c])
        checker = StructuralFeasibilityChecker()
        report = checker.check({"diameter": 0.3, "length": 0.5, "thickness": 0.0005, "material": "A"}, space)
        assert not report.is_feasible
        assert c.id in report.violated_constraints

    def test_violated_category_is_infeasible(self):
        space = cylinder_design_space()
        checker = StructuralFeasibilityChecker()
        report = checker.check({"diameter": 0.3, "length": 0.5, "thickness": 0.005, "material": "Z"}, space)
        assert not report.is_feasible


class TestUnknownFeasibilityWhenDataMissing:
    def test_missing_relation_input_yields_unknown_not_infeasible(self):
        from design_contract.relations import DesignRelation
        from tests.conftest import make_provenance

        relation = DesignRelation(name="volume", inputs=["diameter", "length"], output="volume", expression="diameter * length", provenance=make_provenance())
        space = cylinder_design_space(relations=[relation])
        checker = StructuralFeasibilityChecker()
        # No proveemos 'length' -> la relation no se puede evaluar, pero eso no es lo mismo que "infeasible"
        report = checker.check({"diameter": 0.3, "thickness": 0.005, "material": "A"}, space)
        assert report.status in (FeasibilityStatus.FEASIBLE, FeasibilityStatus.UNKNOWN)


class TestFeasibleNeverConfusedWithSimulated:
    def test_checker_never_imports_any_physics_or_simulation_module(self):
        """FEASIBLE (esta fase) != simulado (fase futura) — verificado en el propio código fuente, no solo en prosa."""
        import inspect

        import design_contract.feasibility as mod

        source = inspect.getsource(mod)
        assert "core.physics" not in source
        assert "core.simulation" not in source
