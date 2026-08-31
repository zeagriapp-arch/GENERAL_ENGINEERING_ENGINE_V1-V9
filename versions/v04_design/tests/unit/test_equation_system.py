import pytest

from core.physics.equation_system import EquationSpec, EquationSystem, EquationValidationError


def _thrust_eq():
    return EquationSpec(
        equation_id="eq-thrust",
        expression="F = mdot*Ve",
        variables={"F": "empuje", "mdot": "flujo másico", "Ve": "velocidad de salida"},
        parameters=["gas_gamma"],
        units={"F": "N", "mdot": "kg/s", "Ve": "m/s"},
    )


def test_validate_passes_when_everything_available():
    system = EquationSystem([_thrust_eq()])
    errors = system.validate(available_variables={"F", "mdot", "Ve"}, available_parameters={"gas_gamma"})
    assert errors == []


def test_validate_detects_missing_variable():
    system = EquationSystem([_thrust_eq()])
    errors = system.validate(available_variables={"F", "mdot"}, available_parameters={"gas_gamma"})
    assert any("Ve" in e for e in errors)


def test_validate_detects_missing_parameter():
    system = EquationSystem([_thrust_eq()])
    errors = system.validate(available_variables={"F", "mdot", "Ve"}, available_parameters=set())
    assert any("gas_gamma" in e for e in errors)


def test_validate_detects_invalid_unit():
    eq = EquationSpec(
        equation_id="bad-unit-eq",
        expression="x = y",
        variables={"x": "a", "y": "b"},
        units={"x": "not_a_real_unit"},
    )
    system = EquationSystem([eq])
    errors = system.validate(available_variables={"x", "y"}, available_parameters=set())
    assert any("unidad inválida" in e for e in errors)


def test_validate_or_raise_raises_on_errors():
    system = EquationSystem([_thrust_eq()])
    with pytest.raises(EquationValidationError):
        system.validate_or_raise(available_variables=set(), available_parameters=set())


def test_get_equation_by_id():
    system = EquationSystem([_thrust_eq()])
    eq = system.get("eq-thrust")
    assert eq.expression == "F = mdot*Ve"
