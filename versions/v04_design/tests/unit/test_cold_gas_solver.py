import pytest

from core.design.repository import create
from core.requirements.schema import Parameter, ParameterType
from domains.satellite.propulsion.simulation_adapters.cold_gas_solver import (
    ColdGasNozzleSolver,
    ColdGasParameterMissingError,
)

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


def test_run_returns_results_with_confidence_and_validity():
    solver = ColdGasNozzleSolver()
    results = solver.run(_design())
    assert results.model_validity == "within_range"
    assert results.confidence == pytest.approx(0.9)
    assert results.data_quality == "high"
    assert "thrust" in results.predictions
    assert results.units["thrust"] == "N"


def test_run_is_deterministic():
    solver = ColdGasNozzleSolver()
    r1 = solver.run(_design())
    r2 = solver.run(_design())
    assert r1.predictions == r2.predictions


def test_run_raises_on_missing_parameters():
    solver = ColdGasNozzleSolver()
    incomplete = create(domain="satellite.propulsion", parameters={})
    with pytest.raises(ColdGasParameterMissingError):
        solver.run(incomplete)


def test_declare_inputs_and_outputs_match_physics_model():
    solver = ColdGasNozzleSolver()
    inputs = solver.declare_inputs()
    outputs = solver.declare_outputs()
    assert "chamber_pressure" in inputs
    assert inputs["chamber_pressure"].unit == "Pa"
    assert "thrust" in outputs
    assert outputs["thrust"].unit == "N"
