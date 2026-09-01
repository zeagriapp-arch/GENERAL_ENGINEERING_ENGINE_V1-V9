from __future__ import annotations

from design_contract.budget import ExperimentBudget


class TestExperimentBudgetFields:
    def test_all_five_fields_from_spec_exist(self):
        for field in ("max_candidates", "max_simulations", "max_compute_time_seconds", "max_cost", "max_iterations"):
            assert field in ExperimentBudget.model_fields

    def test_all_fields_optional_by_default(self):
        budget = ExperimentBudget()
        assert budget.max_candidates is None


class TestExceededBy:
    def test_under_limit_not_exceeded(self):
        budget = ExperimentBudget(max_candidates=100)
        assert not budget.exceeded_by(candidates=50)

    def test_at_limit_is_exceeded(self):
        budget = ExperimentBudget(max_candidates=100)
        assert budget.exceeded_by(candidates=100)

    def test_unset_limit_never_exceeded(self):
        budget = ExperimentBudget(max_candidates=100)
        assert not budget.exceeded_by(cost=1_000_000.0)

    def test_any_dimension_exceeding_triggers_true(self):
        budget = ExperimentBudget(max_candidates=100, max_cost=500.0)
        assert budget.exceeded_by(candidates=1, cost=600.0)
