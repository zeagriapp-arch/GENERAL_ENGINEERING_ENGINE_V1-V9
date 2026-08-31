import pytest

from core.design.repository import DesignModificationError, clone, compare, create, modify
from core.requirements.schema import Parameter, ParameterType


def _sample_design():
    return create(
        domain="satellite.propulsion",
        parameters={
            "area": Parameter(name="area", value=1e-5, unit="m^2", type=ParameterType.FREE, range=(1e-6, 1e-4)),
            "pressure": Parameter(name="pressure", value=5e5, unit="Pa", type=ParameterType.FIXED),
        },
    )


def test_create_design():
    d = _sample_design()
    assert d.domain == "satellite.propulsion"
    assert d.parent_id is None


def test_clone_links_parent():
    d = _sample_design()
    clone_d = clone(d)
    assert clone_d.parent_id == d.id
    assert clone_d.id != d.id


def test_modify_free_variable():
    d = _sample_design()
    modified = modify(d, {"area": 5e-5})
    assert modified.parameters["area"].value == 5e-5
    assert modified.parent_id == d.id
    # inmutabilidad: el original no cambia
    assert d.parameters["area"].value == 1e-5


def test_modify_rejects_fixed_variable():
    d = _sample_design()
    with pytest.raises(DesignModificationError):
        modify(d, {"pressure": 9e5})


def test_modify_rejects_out_of_range():
    d = _sample_design()
    with pytest.raises(DesignModificationError):
        modify(d, {"area": 1.0})  # fuera del range (1e-6, 1e-4)


def test_modify_rejects_unknown_parameter():
    d = _sample_design()
    with pytest.raises(DesignModificationError):
        modify(d, {"does_not_exist": 1.0})


def test_compare_detects_diff():
    a = _sample_design()
    b = modify(a, {"area": 2e-5})
    diff = compare(a, b)
    assert "area" in diff
    assert diff["area"]["a"] == 1e-5
    assert diff["area"]["b"] == 2e-5
    assert "pressure" not in diff
