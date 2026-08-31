import pytest
from hypothesis import given, strategies as st

from core.requirements.schema import Parameter, ParameterType
from core.validation.dimensional_analysis import (
    DimensionalAnalysisError,
    are_compatible,
    convert,
    validate,
    validate_unit,
)


def test_valid_unit_passes():
    assert validate_unit("N").valid
    assert validate_unit("kg/s").valid
    assert validate_unit("Pa").valid


def test_none_unit_is_explicitly_dimensionless_and_valid():
    assert validate_unit(None).valid


def test_invalid_unit_fails():
    result = validate_unit("not_a_real_unit_xyz")
    assert not result.valid
    assert result.reason is not None


def test_validate_collects_errors_by_parameter_name():
    params = {
        "thrust": Parameter(name="thrust", value=1.0, unit="N", type=ParameterType.FIXED),
        "bad_param": Parameter(name="bad_param", value=1.0, unit="bogus_unit", type=ParameterType.FIXED),
    }
    errors = validate(params)
    assert len(errors) == 1
    assert "bad_param" in errors[0]


def test_compatible_units():
    assert are_compatible("N", "kg*m/s^2")
    assert are_compatible(None, None)
    assert not are_compatible("N", "Pa")
    assert not are_compatible(None, "N")


def test_convert_compatible_units():
    assert convert(1000, "g", "kg") == pytest.approx(1.0)


def test_convert_incompatible_units_raises():
    with pytest.raises(DimensionalAnalysisError):
        convert(1.0, "N", "Pa")


@given(st.floats(min_value=0.001, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_convert_round_trip_is_stable(value):
    """Property-based: convertir ida y vuelta debe devolver el valor original."""
    converted = convert(value, "m", "mm")
    back = convert(converted, "mm", "m")
    assert back == pytest.approx(value, rel=1e-6)
