import pytest

from core.design.design_space import DesignSpace, DesignSpaceError
from core.requirements.schema import Objective, Parameter, ParameterType, Requirements


def _requirements(**var_overrides):
    variables = {
        "fixed_a": Parameter(name="fixed_a", value=5.0, unit="Pa", type=ParameterType.FIXED),
        "free_b": Parameter(name="free_b", value=1.0, unit="m", type=ParameterType.FREE, range=(0.5, 2.0)),
    }
    variables.update(var_overrides)
    return Requirements(
        problem="test",
        domain="generic.mechanics",
        objectives=[Objective(name="obj", direction="maximize", metric="m")],
        variables=variables,
    )


def test_from_requirements_splits_free_and_fixed():
    space = DesignSpace.from_requirements(_requirements())
    assert "free_b" in space.variables
    assert "fixed_a" in space.fixed_parameters
    assert space.variables["free_b"].lower_bound == 0.5
    assert space.variables["free_b"].upper_bound == 2.0


def test_from_requirements_raises_when_free_variable_has_no_range():
    bad_free = Parameter(name="bad_free", value=1.0, type=ParameterType.FREE, range=None)
    with pytest.raises(DesignSpaceError):
        DesignSpace.from_requirements(_requirements(bad_free=bad_free))


def test_from_requirements_includes_operating_conditions_as_fixed():
    req = _requirements()
    req.operating_conditions["gas"] = Parameter(name="gas", value="N2", type=ParameterType.FIXED)
    space = DesignSpace.from_requirements(req)
    assert "gas" in space.fixed_parameters


def test_variable_contains():
    space = DesignSpace.from_requirements(_requirements())
    var = space.variables["free_b"]
    assert var.contains(1.0)
    assert not var.contains(3.0)


def test_all_values_with_merges_fixed_and_candidate():
    space = DesignSpace.from_requirements(_requirements())
    values = space.all_values_with({"free_b": 1.5})
    assert values["fixed_a"] == 5.0
    assert values["free_b"] == 1.5
