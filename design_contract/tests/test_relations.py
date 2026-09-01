from __future__ import annotations

import pytest

from design_contract.relations import (
    CandidateRelation,
    ExpressionEvaluationError,
    UnsafeExpressionError,
    evaluate_expression,
    register_relation_function,
    validate_candidate_relation,
    validate_expression_structure,
)
from tests.conftest import make_provenance


class TestValidExpressions:
    def test_arithmetic(self):
        assert evaluate_expression("radius * 2", {"radius": 3.0}) == 6.0

    def test_volume_of_cylinder(self):
        result = evaluate_expression("3.14159 * radius**2 * length", {"radius": 1.0, "length": 2.0})
        assert result == pytest.approx(6.28318, rel=1e-4)

    def test_comparison_returns_bool(self):
        assert evaluate_expression("thickness >= 0.005", {"thickness": 0.01}) is True
        assert evaluate_expression("thickness >= 0.005", {"thickness": 0.001}) is False

    def test_registered_function_call(self):
        register_relation_function("double", lambda x: x * 2)
        assert evaluate_expression("double(radius)", {"radius": 4.0}) == 8.0

    def test_builtin_min_max(self):
        assert evaluate_expression("min(a, b)", {"a": 3, "b": 5}) == 3
        assert evaluate_expression("max(a, b)", {"a": 3, "b": 5}) == 5


class TestDependencyOnMultipleVariables:
    def test_volume_depends_on_radius_and_length(self):
        namespace = {"radius": 0.15, "length": 0.6}
        result = evaluate_expression("3.14159 * radius**2 * length", namespace)
        assert result > 0


class TestInvalidExpressions:
    def test_syntax_error(self):
        with pytest.raises(ExpressionEvaluationError):
            evaluate_expression("radius * * 2", {"radius": 1.0})

    def test_missing_variable(self):
        with pytest.raises(ExpressionEvaluationError):
            evaluate_expression("radius * length", {"radius": 1.0})

    def test_unregistered_function(self):
        with pytest.raises(UnsafeExpressionError):
            evaluate_expression("nonexistent_function(radius)", {"radius": 1.0})


class TestUnsafeExpressionsRejected:
    """Sección 31 — la parte más crítica de seguridad de esta fase."""

    @pytest.mark.parametrize(
        "expression",
        [
            "__import__('os').system('echo pwned')",
            "open('/etc/passwd').read()",
            "().__class__.__bases__[0]",
            "[x for x in range(10)]",
            "lambda x: x",
            "exec('1')",
            "eval('1')",
            "a.b.c",
            "a[0]",
            "{1: 2}",
            "a if True else b",
        ],
    )
    def test_dangerous_construct_never_executes(self, expression):
        with pytest.raises((UnsafeExpressionError, ExpressionEvaluationError)):
            evaluate_expression(expression, {"a": 1, "b": 2})

    def test_keyword_arguments_rejected(self):
        with pytest.raises(UnsafeExpressionError):
            evaluate_expression("round(a, ndigits=2)", {"a": 1.234})


class TestStructuralValidationWithoutEvaluating:
    def test_valid_structure_no_errors(self):
        errors = validate_expression_structure("radius * 2", allowed_names={"radius"})
        assert errors == []

    def test_name_outside_allowed_set_is_an_error(self):
        errors = validate_expression_structure("radius * length", allowed_names={"radius"})
        assert any("length" in e for e in errors)

    def test_unsafe_construct_reported_without_raising(self):
        errors = validate_expression_structure("__import__('os')", allowed_names=set())
        assert errors  # no excepción — lista de errores


class TestCandidateRelationValidation:
    def test_valid_candidate_relation_produces_design_relation(self):
        candidate = CandidateRelation(
            name="volume", inputs=["radius", "length"], output="volume", expression="3.14159 * radius**2 * length", provenance=make_provenance()
        )
        relation, errors = validate_candidate_relation(candidate, known_variable_names={"radius", "length"})
        assert errors == []
        assert relation is not None
        assert relation.evaluate({"radius": 1.0, "length": 1.0}) == pytest.approx(3.14159)

    def test_unknown_input_variable_rejected(self):
        candidate = CandidateRelation(name="volume", inputs=["radius"], output="volume", expression="radius * 2", provenance=make_provenance())
        relation, errors = validate_candidate_relation(candidate, known_variable_names=set())
        assert relation is None
        assert any("radius" in e for e in errors)

    def test_output_cannot_be_its_own_input(self):
        candidate = CandidateRelation(name="bad", inputs=["x"], output="x", expression="x * 2", provenance=make_provenance())
        relation, errors = validate_candidate_relation(candidate, known_variable_names={"x"})
        assert relation is None
        assert any("output" in e.lower() for e in errors)

    def test_llm_proposal_never_gains_execution_authority_before_validation(self):
        """LLM proposal != trusted relation (sección 11) — una expresión insegura nunca produce un DesignRelation."""
        malicious = CandidateRelation(
            name="evil", inputs=["radius"], output="volume", expression="__import__('os').system('rm -rf /')", provenance=make_provenance()
        )
        relation, errors = validate_candidate_relation(malicious, known_variable_names={"radius"})
        assert relation is None
        assert errors  # rechazado, nunca se evalúa
