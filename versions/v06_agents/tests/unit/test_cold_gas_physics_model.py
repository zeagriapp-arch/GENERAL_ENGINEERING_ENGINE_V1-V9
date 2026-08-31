import pytest

from core.design.repository import create
from core.physics.interfaces import PhysicsInputs
from core.requirements.schema import Parameter, ParameterType
from domains.satellite.propulsion.physics_models.cold_gas_thruster import ColdGasThrusterPhysicsModel

N2_CASE = {
    "chamber_pressure": 5e5,
    "chamber_temperature": 300.0,
    "throat_area": 1e-6,
    "nozzle_exit_area": 1e-5,
    "ambient_pressure": 0.0,
    "gas_gamma": 1.4,
    "gas_constant": 296.8,
}


def _design(**overrides):
    params = {**N2_CASE, **overrides}
    return create(
        domain="satellite.propulsion",
        parameters={
            name: Parameter(name=name, value=value, unit=None, type=ParameterType.FIXED)
            for name, value in params.items()
        },
    )


def test_applies_to_valid_design():
    model = ColdGasThrusterPhysicsModel()
    assert model.applies_to(_design())


def test_does_not_apply_to_other_domain():
    model = ColdGasThrusterPhysicsModel()
    d = _design()
    d.domain = "satellite.thermal"
    assert not model.applies_to(d)


def test_does_not_apply_when_parameters_missing():
    model = ColdGasThrusterPhysicsModel()
    design = create(domain="satellite.propulsion", parameters={})
    assert not model.applies_to(design)


def test_compute_within_range_gives_physically_plausible_isp():
    model = ColdGasThrusterPhysicsModel()
    outputs = model.compute(PhysicsInputs(values=N2_CASE))
    assert outputs.within_validity_range
    # Isp típico de thrusters de N2 de gas frío está en el rango 50-75 s
    # (orden de magnitud conocido, no un número exacto copiado de fuente).
    assert 50.0 < outputs.values["specific_impulse"] < 90.0
    assert outputs.values["exit_mach"] > 1.0  # tobera divergente -> supersónico


def test_compute_marks_out_of_range_when_chamber_pressure_below_ambient():
    model = ColdGasThrusterPhysicsModel()
    bad_case = {**N2_CASE, "ambient_pressure": 1e6}  # p0 > pt
    outputs = model.compute(PhysicsInputs(values=bad_case))
    assert not outputs.within_validity_range
    assert any("ambient_pressure" in note for note in outputs.validity_notes)


def test_compute_marks_out_of_range_when_area_ratio_extreme():
    model = ColdGasThrusterPhysicsModel()
    bad_case = {**N2_CASE, "nozzle_exit_area": 1e-6 * 10000}  # area_ratio = 10000 > 500
    outputs = model.compute(PhysicsInputs(values=bad_case))
    assert not outputs.within_validity_range


def test_area_ratio_of_one_gives_mach_one():
    model = ColdGasThrusterPhysicsModel()
    case = {**N2_CASE, "nozzle_exit_area": N2_CASE["throat_area"]}  # Ae == At
    outputs = model.compute(PhysicsInputs(values=case))
    assert outputs.values["exit_mach"] == pytest.approx(1.0, abs=1e-6)


def test_assumptions_are_declared_and_nonempty():
    model = ColdGasThrusterPhysicsModel()
    assumptions = model.assumptions()
    assert len(assumptions) >= 4
    assert all(isinstance(a, str) for a in assumptions)
