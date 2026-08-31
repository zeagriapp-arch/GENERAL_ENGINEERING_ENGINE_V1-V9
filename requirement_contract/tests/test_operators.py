from __future__ import annotations

import pytest

from requirement_contract.operators import DEFAULT_APPROX_RELATIVE_TOLERANCE, OperatorEvaluationError, as_interval, evaluate
from requirement_contract.schema import Operator


class TestComparisonOperators:
    @pytest.mark.parametrize(
        "operator,actual,target,expected",
        [
            (Operator.EQ, 5, 5, True),
            (Operator.EQ, 5, 6, False),
            (Operator.NEQ, 5, 6, True),
            (Operator.NEQ, 5, 5, False),
            (Operator.LT, 4, 5, True),
            (Operator.LT, 5, 5, False),
            (Operator.LTE, 5, 5, True),
            (Operator.LTE, 6, 5, False),
            (Operator.GT, 6, 5, True),
            (Operator.GT, 5, 5, False),
            (Operator.GTE, 5, 5, True),
            (Operator.GTE, 4, 5, False),
        ],
    )
    def test_numeric_comparisons(self, operator, actual, target, expected):
        assert evaluate(operator, actual, target) is expected

    def test_approx_within_tolerance_true(self):
        assert evaluate(Operator.APPROX, 100.0, 100.05, approx_relative_tolerance=0.001) is True

    def test_approx_outside_tolerance_false(self):
        assert evaluate(Operator.APPROX, 100.0, 110.0, approx_relative_tolerance=DEFAULT_APPROX_RELATIVE_TOLERANCE) is False

    def test_approx_requires_numeric(self):
        with pytest.raises(OperatorEvaluationError):
            evaluate(Operator.APPROX, "a", "b")


class TestMembershipOperators:
    def test_in_true(self):
        assert evaluate(Operator.IN, "red", ["red", "green", "blue"]) is True

    def test_in_false(self):
        assert evaluate(Operator.IN, "yellow", ["red", "green", "blue"]) is False

    def test_not_in_true(self):
        assert evaluate(Operator.NOT_IN, "yellow", ["red", "green", "blue"]) is True

    def test_in_requires_list_target(self):
        with pytest.raises(OperatorEvaluationError):
            evaluate(Operator.IN, "red", "red")

    def test_comparison_operator_rejects_list_target(self):
        with pytest.raises(OperatorEvaluationError):
            evaluate(Operator.LTE, 5, [1, 2, 3])


class TestOrderingRequiresNumeric:
    def test_lt_on_strings_raises(self):
        with pytest.raises(OperatorEvaluationError):
            evaluate(Operator.LT, "a", "b")


class TestAsInterval:
    def test_lte_gives_upper_bound(self):
        assert as_interval(Operator.LTE, 20.0) == (float("-inf"), 20.0)

    def test_gte_gives_lower_bound(self):
        assert as_interval(Operator.GTE, 30.0) == (30.0, float("inf"))

    def test_eq_gives_point_interval(self):
        assert as_interval(Operator.EQ, 5.0) == (5.0, 5.0)

    def test_neq_not_representable_as_interval(self):
        assert as_interval(Operator.NEQ, 5.0) is None

    def test_non_numeric_not_representable(self):
        assert as_interval(Operator.EQ, "red") is None
