"""
Verifica que core.simulation.engine es domain-agnóstico: sin un solver
registrado, devuelve UNKNOWN explícito (Principio Fundamental, sección 2)
igual que el default de Orchestrator en Phase 1; con un solver
registrado desde fuera (simulando el bootstrap de aplicación), delega
correctamente.
"""
import pytest

from core.design.repository import create
from core.requirements.schema import Parameter, ParameterType
from core.simulation import engine as simulation_engine
from domains.satellite.propulsion.simulation_adapters.cold_gas_solver import ColdGasNozzleSolver

N2_CASE = {
    "chamber_pressure": 5e5,
    "chamber_temperature": 300.0,
    "throat_area": 1e-6,
    "nozzle_exit_area": 1e-5,
    "ambient_pressure": 0.0,
    "gas_gamma": 1.4,
    "gas_constant": 296.8,
}


def _design(domain="satellite.propulsion"):
    return create(
        domain=domain,
        parameters={
            name: Parameter(name=name, value=value, unit=None, type=ParameterType.FIXED)
            for name, value in N2_CASE.items()
        },
    )


@pytest.fixture(autouse=True)
def _clean_registry():
    simulation_engine.unregister_all()
    yield
    simulation_engine.unregister_all()


def test_run_without_registered_solver_returns_unknown():
    results = simulation_engine.run(_design())
    assert results.model_validity == "unknown"
    assert results.confidence is None


def test_run_with_registered_solver_delegates_correctly():
    simulation_engine.register_solver("satellite.propulsion", ColdGasNozzleSolver())
    results = simulation_engine.run(_design())
    assert results.model_validity == "within_range"
    assert "thrust" in results.predictions


def test_run_uses_domain_specific_solver_only():
    simulation_engine.register_solver("satellite.propulsion", ColdGasNozzleSolver())
    other_domain_design = _design(domain="satellite.thermal")
    results = simulation_engine.run(other_domain_design)
    assert results.model_validity == "unknown"  # no hay solver para satellite.thermal
