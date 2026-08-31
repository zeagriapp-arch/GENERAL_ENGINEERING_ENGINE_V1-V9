"""
Benchmarks de V&V del cold-gas thruster (sección 31). Deben pasar antes
de habilitar Discovery Mode para este dominio. Cubren un rango de casos
representativos: distintos gases (N2, He, CO2 aproximados), distintas
razones de área, y el caso límite área_ratio=1.
"""
import pytest

from domains.satellite.propulsion.validation_benchmarks import (
    check_isp_identity,
    check_mach_area_roundtrip,
    check_mass_continuity,
    run_all_benchmarks,
)
from domains.satellite.propulsion.physics_models.cold_gas_thruster import ColdGasThrusterPhysicsModel
from core.physics.interfaces import PhysicsInputs

CASES = [
    # N2, area ratio moderado
    dict(chamber_pressure=5e5, chamber_temperature=300.0, throat_area=1e-6, nozzle_exit_area=1e-5,
         ambient_pressure=0.0, gas_gamma=1.4, gas_constant=296.8),
    # He, area ratio alto
    dict(chamber_pressure=1e6, chamber_temperature=280.0, throat_area=5e-7, nozzle_exit_area=2.5e-5,
         ambient_pressure=0.0, gas_gamma=1.66, gas_constant=2077.0),
    # CO2 aprox, area ratio bajo
    dict(chamber_pressure=3e5, chamber_temperature=250.0, throat_area=2e-6, nozzle_exit_area=6e-6,
         ambient_pressure=0.0, gas_gamma=1.28, gas_constant=188.9),
    # Caso límite: area_ratio == 1 (sin sección divergente, M=1 en salida)
    dict(chamber_pressure=5e5, chamber_temperature=300.0, throat_area=1e-6, nozzle_exit_area=1e-6,
         ambient_pressure=0.0, gas_gamma=1.4, gas_constant=296.8),
]


@pytest.mark.parametrize("case", CASES, ids=["N2_moderate", "He_high_ratio", "CO2_low_ratio", "area_ratio_one"])
def test_isp_identity_benchmark(case):
    model = ColdGasThrusterPhysicsModel()
    outputs = model.compute(PhysicsInputs(values=case))
    result = check_isp_identity(outputs)
    assert result.passed, result.detail


@pytest.mark.parametrize("case", CASES, ids=["N2_moderate", "He_high_ratio", "CO2_low_ratio", "area_ratio_one"])
def test_mass_continuity_benchmark(case):
    model = ColdGasThrusterPhysicsModel()
    outputs = model.compute(PhysicsInputs(values=case))
    result = check_mass_continuity(outputs, gas_constant=case["gas_constant"], throat_area=case["throat_area"])
    assert result.passed, result.detail


@pytest.mark.parametrize("case", CASES, ids=["N2_moderate", "He_high_ratio", "CO2_low_ratio", "area_ratio_one"])
def test_mach_area_roundtrip_benchmark(case):
    area_ratio = case["nozzle_exit_area"] / case["throat_area"]
    result = check_mach_area_roundtrip(area_ratio, case["gas_gamma"])
    assert result.passed, result.detail


def test_run_all_benchmarks_all_pass():
    results = run_all_benchmarks(CASES)
    failed = [r for r in results if not r.passed]
    assert not failed, f"Benchmarks fallidos: {[(r.name, r.detail) for r in failed]}"
