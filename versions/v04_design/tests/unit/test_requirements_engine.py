import pytest

from core.requirements.engine import RequirementsEngine, RequirementsValidationError
from core.requirements.schema import Objective, Parameter, ParameterType


def test_build_valid_requirements():
    eng = RequirementsEngine()
    req = eng.build(
        problem="Maximizar Isp",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        variables={
            "area": Parameter(name="area", value=1e-5, unit="m^2", type=ParameterType.FREE, range=(1e-6, 1e-4)),
        },
    )
    assert req.problem == "Maximizar Isp"
    assert "area" in req.free_variables()


def test_build_rejects_invalid_unit():
    eng = RequirementsEngine()
    with pytest.raises(RequirementsValidationError) as exc_info:
        eng.build(
            problem="x",
            domain="satellite.propulsion",
            objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
            variables={"bad": Parameter(name="bad", value=1.0, unit="not_a_unit", type=ParameterType.FIXED)},
        )
    assert any("bad" in e for e in exc_info.value.errors)


def test_build_rejects_missing_objectives():
    eng = RequirementsEngine()
    with pytest.raises(RequirementsValidationError):
        eng.build(problem="x", domain="satellite.propulsion")
