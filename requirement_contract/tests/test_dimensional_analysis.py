from __future__ import annotations

from requirement_contract.validators.base import Severity, ValidationContext
from requirement_contract.validators.dimensional_validator import (
    KNOWN_PARAMETER_DIMENSIONS,
    DimensionalValidator,
    register_parameter_dimension,
)
from tests.conftest import make_candidate


class TestDimensionalCompatibility:
    def test_mass_in_kg_is_compatible(self):
        candidate = make_candidate(parameter="mass", value_unit="kg")
        result = DimensionalValidator().validate(candidate, context=ValidationContext())
        assert result.passed

    def test_mass_in_pounds_is_compatible_different_unit_same_dimension(self):
        candidate = make_candidate(parameter="mass", value_unit="lb")
        result = DimensionalValidator().validate(candidate, context=ValidationContext())
        assert result.passed


class TestDimensionalIncompatibility:
    def test_mass_in_seconds_is_rejected(self):
        """El ejemplo explícito de la especificación: mass <= 500 seconds."""
        candidate = make_candidate(parameter="mass", value_unit="seconds", value_original=500.0)
        result = DimensionalValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "mass" in errors[0].message and "seconds" in errors[0].message

    def test_temperature_in_pascals_is_rejected(self):
        candidate = make_candidate(parameter="temperature", value_unit="Pa", value_original=300.0)
        result = DimensionalValidator().validate(candidate, context=ValidationContext())
        assert not result.passed

    def test_uncertainty_unit_dimensionally_incompatible_is_rejected(self):
        from requirement_contract.schema import Uncertainty

        candidate = make_candidate(
            parameter="mass",
            value_unit="kg",
            uncertainty=Uncertainty(unit="seconds"),
        )
        result = DimensionalValidator().validate(candidate, context=ValidationContext())
        assert not result.passed
        assert any(i.field == "uncertainty.unit" for i in result.issues)


class TestUnknownParameterIsNotAnError:
    def test_unrecognized_parameter_name_never_errors_out(self):
        """Un parameter que el registro no conoce no debe generar falsos positivos."""
        candidate = make_candidate(parameter="widget_gizmo_factor", value_unit="kg")
        result = DimensionalValidator().validate(candidate, context=ValidationContext())
        assert result.passed


class TestRegistryIsExtensibleAndDomainAgnosticByDefault:
    def test_default_registry_has_no_aerospace_specific_vocabulary(self):
        forbidden_domain_terms = {"thrust", "specific_impulse", "chamber_pressure", "isp", "delta_v"}
        assert forbidden_domain_terms.isdisjoint(KNOWN_PARAMETER_DIMENSIONS.keys())

    def test_default_registry_covers_universal_si_quantities(self):
        for name in ("mass", "length", "time", "temperature", "force", "pressure", "energy"):
            assert name in KNOWN_PARAMETER_DIMENSIONS

    def test_register_parameter_dimension_extends_without_modifying_module(self):
        register_parameter_dimension("widget_gizmo_factor", "kg")
        try:
            candidate = make_candidate(parameter="widget_gizmo_factor", value_unit="seconds")
            result = DimensionalValidator().validate(candidate, context=ValidationContext())
            assert not result.passed
        finally:
            del KNOWN_PARAMETER_DIMENSIONS["widget_gizmo_factor"]  # no contaminar otros tests
