import math

import pytest

from core.design.repository import create
from core.physics.interfaces import PhysicsInputs
from core.requirements.schema import Parameter, ParameterType
from core.physics.benchmark_models.constant_acceleration import ConstantAccelerationModel
from core.physics.benchmark_models.mass_spring_oscillator import MassSpringOscillatorModel, analytical_solution


def test_constant_acceleration_matches_closed_form():
    model = ConstantAccelerationModel()
    outputs = model.compute(
        PhysicsInputs(values={"initial_position": 0.0, "initial_velocity": 5.0, "acceleration": -9.8, "time": 1.0})
    )
    assert outputs.values["position"] == pytest.approx(5.0 - 4.9)
    assert outputs.values["velocity"] == pytest.approx(5.0 - 9.8)
    assert outputs.within_validity_range


def test_constant_acceleration_applies_to_generic_mechanics_domain():
    model = ConstantAccelerationModel()
    design = create(
        domain="generic.mechanics",
        parameters={
            name: Parameter(name=name, value=1.0, type=ParameterType.FIXED)
            for name in ["initial_position", "initial_velocity", "acceleration", "time"]
        },
    )
    assert model.applies_to(design)


def test_mass_spring_oscillator_matches_analytical_solution():
    model = MassSpringOscillatorModel()
    mass, k, x0, v0, t = 2.0, 8.0, 0.5, 1.0, 3.0
    outputs = model.compute(
        PhysicsInputs(
            values={"mass": mass, "spring_constant": k, "initial_position": x0, "initial_velocity": v0, "time": t}
        )
    )
    x_expected, v_expected = analytical_solution(mass, k, x0, v0, t)
    assert outputs.values["position"] == pytest.approx(x_expected, rel=1e-6)
    assert outputs.values["velocity"] == pytest.approx(v_expected, rel=1e-6)


def test_mass_spring_oscillator_energy_conservation():
    """Chequeo físico independiente: energía mecánica total debe conservarse (sin amortiguación)."""
    model = MassSpringOscillatorModel()
    mass, k, x0, v0 = 1.0, 4.0, 1.0, 0.0
    e0 = 0.5 * k * x0**2 + 0.5 * mass * v0**2

    for t in [0.5, 1.3, 2.7, 5.0]:
        outputs = model.compute(
            PhysicsInputs(values={"mass": mass, "spring_constant": k, "initial_position": x0, "initial_velocity": v0, "time": t})
        )
        x, v = outputs.values["position"], outputs.values["velocity"]
        e = 0.5 * k * x**2 + 0.5 * mass * v**2
        assert e == pytest.approx(e0, rel=1e-6), f"Energía no conservada en t={t}"
