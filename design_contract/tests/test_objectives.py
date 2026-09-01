from __future__ import annotations

from design_contract.objectives import DesignObjective, ObjectiveDirection, ObjectiveVector


class TestMinimizeMaximize:
    def test_minimize_objective(self):
        obj = DesignObjective(name="mass", direction=ObjectiveDirection.MINIMIZE, metric="mass")
        assert obj.direction == ObjectiveDirection.MINIMIZE

    def test_maximize_objective(self):
        obj = DesignObjective(name="performance", direction=ObjectiveDirection.MAXIMIZE, metric="performance")
        assert obj.direction == ObjectiveDirection.MAXIMIZE

    def test_weight_and_priority_are_optional(self):
        obj = DesignObjective(name="cost", direction=ObjectiveDirection.MINIMIZE, metric="cost")
        assert obj.weight is None
        assert obj.priority is None


class TestMultipleObjectivesNotReducedToOneScore:
    def test_objective_vector_preserves_every_axis(self):
        vector = ObjectiveVector(values={"performance": 0.82, "mass": 14.3, "cost": 1200.0, "reliability": 0.97})
        assert len(vector.values) == 4
        assert vector.values["mass"] == 14.3

    def test_no_single_score_field_exists(self):
        vector = ObjectiveVector(values={"a": 1.0})
        assert "score" not in vector.model_dump()


class TestParetoDominance:
    def _objectives(self):
        return [
            DesignObjective(name="performance", direction=ObjectiveDirection.MAXIMIZE, metric="performance"),
            DesignObjective(name="mass", direction=ObjectiveDirection.MINIMIZE, metric="mass"),
        ]

    def test_strictly_better_in_all_dominates(self):
        a = ObjectiveVector(values={"performance": 0.9, "mass": 10.0})
        b = ObjectiveVector(values={"performance": 0.7, "mass": 15.0})
        assert a.dominates(b, self._objectives())
        assert not b.dominates(a, self._objectives())

    def test_better_in_one_worse_in_other_neither_dominates(self):
        a = ObjectiveVector(values={"performance": 0.9, "mass": 15.0})  # mejor performance, peor mass
        b = ObjectiveVector(values={"performance": 0.7, "mass": 10.0})  # peor performance, mejor mass
        assert not a.dominates(b, self._objectives())
        assert not b.dominates(a, self._objectives())

    def test_identical_vectors_do_not_dominate_each_other(self):
        a = ObjectiveVector(values={"performance": 0.8, "mass": 12.0})
        b = ObjectiveVector(values={"performance": 0.8, "mass": 12.0})
        assert not a.dominates(b, self._objectives())

    def test_no_comparable_objectives_never_dominates(self):
        a = ObjectiveVector(values={"cost": 100.0})
        b = ObjectiveVector(values={"performance": 0.5})
        assert not a.dominates(b, self._objectives())
