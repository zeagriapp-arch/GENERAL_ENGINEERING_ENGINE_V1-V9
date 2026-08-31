from __future__ import annotations

import pytest

from requirement_contract.schema import RequirementType, Uncertainty, ValidityRange, Validity
from requirement_contract.validators.base import Severity, ValidationContext
from requirement_contract.validators.unit_validator import UnitValidator, normalize_value
from tests.conftest import make_candidate


class TestNormalizeValuePreservesOriginal:
    def test_lb_converts_to_kg_and_preserves_original(self):
        normalized_value, normalized_unit, notes = normalize_value(20.0, "lb")
        assert normalized_unit == "kg"
        assert normalized_value == pytest.approx(9.0718474, rel=1e-6)
        assert notes  # se registró explícitamente la conversión, nunca silenciosa

    def test_minute_converts_to_seconds(self):
        normalized_value, normalized_unit, notes = normalize_value(2.0, "minute")
        assert normalized_unit == "s"
        assert normalized_value == pytest.approx(120.0)

    def test_kg_to_kg_is_still_recorded_as_conversion_with_notes(self):
        normalized_value, normalized_unit, notes = normalize_value(20.0, "kg")
        assert normalized_unit == "kg"
        assert normalized_value == pytest.approx(20.0)
        assert notes

    def test_no_unit_means_no_conversion(self):
        normalized_value, normalized_unit, notes = normalize_value(3, None)
        assert normalized_unit is None
        assert normalized_value == 3
        assert "adimensional" in notes[0].lower()

    def test_non_numeric_value_with_unit_is_preserved_unconverted(self):
        normalized_value, normalized_unit, notes = normalize_value("N2", "kg")
        assert normalized_value == "N2"
        assert normalized_unit == "kg"

    def test_list_value_converted_elementwise(self):
        normalized_value, normalized_unit, notes = normalize_value([1.0, 2.0], "lb")
        assert normalized_unit == "kg"
        assert normalized_value[0] == pytest.approx(0.45359237, rel=1e-6)
        assert normalized_value[1] == pytest.approx(0.90718474, rel=1e-6)

    def test_invalid_unit_never_raises_returns_unconverted_with_note(self):
        """normalize_value() nunca crashea ante una unidad desconocida — UnitValidator
        es quien rechaza el candidato; esta función solo se usa best-effort en otros
        validadores (ej. ConflictValidator) que pueden recibir un candidato aún no
        validado."""
        normalized_value, normalized_unit, notes = normalize_value(500.0, "glorbins")
        assert normalized_value == 500.0
        assert normalized_unit == "glorbins"
        assert any("inválida" in n for n in notes)

    def test_compound_derived_unit_normalizes_to_base_si_form(self):
        # Pa se compone en base SI como kg/(m*s^2) — comportamiento esperado
        # de pint, documentado aquí explícitamente para que no sea sorpresa.
        normalized_value, normalized_unit, notes = normalize_value(1.0, "bar")
        assert normalized_value == pytest.approx(100000.0)
        assert "kg" in normalized_unit and "m" in normalized_unit and "s" in normalized_unit


class TestUnitValidator:
    def test_valid_unit_passes(self):
        candidate = make_candidate(value_unit="kg")
        result = UnitValidator().validate(candidate, context=ValidationContext())
        assert result.passed

    def test_unknown_unit_fails(self):
        candidate = make_candidate(value_unit="glorbins")
        result = UnitValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        assert any(i.severity == Severity.ERROR and i.field == "value_unit" for i in result.issues)

    def test_none_unit_is_valid_dimensionless(self):
        candidate = make_candidate(parameter="ratio", value_unit=None, value_original=0.5)
        result = UnitValidator().validate(candidate, context=ValidationContext())
        assert result.passed

    def test_invalid_uncertainty_unit_fails(self):
        candidate = make_candidate(uncertainty=Uncertainty(unit="not-a-real-unit"))
        result = UnitValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        assert any(i.field == "uncertainty.unit" for i in result.issues)

    def test_invalid_validity_unit_fails(self):
        candidate = make_candidate(
            validity=Validity(conditions={"temperature": ValidityRange(min=250, max=400, unit="not-a-unit")})
        )
        result = UnitValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        assert any("validity.conditions.temperature.unit" == i.field for i in result.issues)
