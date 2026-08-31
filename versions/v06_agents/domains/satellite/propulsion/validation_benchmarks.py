"""
Validation Benchmarks del cold-gas thruster (sección 31).

No dependemos de un único "número mágico" de un libro de texto (riesgo
de copiar un valor sin poder verificarlo). En su lugar, usamos
identidades algebraicas EXACTAS que cualquier solución física correcta
de tobera ideal debe satisfacer — si una de estas falla, hay un error de
signo/despeje en el código, sin importar qué caso numérico se use:

1. Identidad Isp: Isp = F/(mdot*g0) debe coincidir con Isp = CF*c*/g0
   (dos caminos algebraicos independientes al mismo resultado).
2. Continuidad de masa: el flujo másico en la garganta (elección atorada)
   debe igualar rho_e * Ae * Ve en la salida (conservación de masa entre
   dos secciones de la misma tobera).
3. Round-trip Mach-área: resolver M desde area_ratio y luego recalcular
   area_ratio desde ese M debe devolver el area_ratio original.

Antes de habilitar Discovery Mode (sección 31), estos benchmarks deben
pasar sobre un conjunto de casos representativos.
"""
from __future__ import annotations

from dataclasses import dataclass

from domains.satellite.propulsion.physics_models.cold_gas_thruster import (
    G0,
    _area_ratio_from_mach,
    ColdGasThrusterPhysicsModel,
)
from core.physics.interfaces import PhysicsInputs, PhysicsOutputs


@dataclass
class BenchmarkResult:
    name: str
    passed: bool
    relative_error: float
    detail: str = ""


def check_isp_identity(outputs: PhysicsOutputs, *, tolerance: float = 1e-9) -> BenchmarkResult:
    v = outputs.values
    isp_from_thrust = v["thrust"] / (v["mass_flow_rate"] * G0)
    isp_from_cstar_cf = v["characteristic_velocity"] * v["thrust_coefficient"] / G0
    rel_error = abs(isp_from_thrust - isp_from_cstar_cf) / abs(isp_from_thrust)
    return BenchmarkResult(
        name="isp_identity",
        passed=rel_error <= tolerance,
        relative_error=rel_error,
        detail=f"Isp(F/mdot/g0)={isp_from_thrust:.6f} vs Isp(CF*c*/g0)={isp_from_cstar_cf:.6f}",
    )


def check_mass_continuity(
    outputs: PhysicsOutputs, *, gas_constant: float, throat_area: float, tolerance: float = 1e-9
) -> BenchmarkResult:
    """
    Conservación de masa: el flujo másico atorado en la garganta
    (`eq-choked-mass-flow`) debe igualar rho_e * Ae * Ve calculado en la
    salida a partir de las relaciones isentrópicas (`doc-isentropic-exit-relations`)
    — son dos caminos físicos independientes al mismo flujo másico.
    """
    v = outputs.values
    exit_area = throat_area * v["area_ratio"]
    rho_e = v["exit_pressure"] / (gas_constant * v["exit_temperature"])
    mdot_continuity = rho_e * exit_area * v["exit_velocity"]
    mdot_choked = v["mass_flow_rate"]
    rel_error = abs(mdot_continuity - mdot_choked) / abs(mdot_choked)
    return BenchmarkResult(
        name="mass_continuity",
        passed=rel_error <= tolerance,
        relative_error=rel_error,
        detail=f"mdot_choked={mdot_choked:.8f} vs mdot_continuity(rho_e*Ae*Ve)={mdot_continuity:.8f}",
    )


def check_mach_area_roundtrip(area_ratio: float, gamma: float, *, tolerance: float = 1e-8) -> BenchmarkResult:
    from domains.satellite.propulsion.physics_models.cold_gas_thruster import _solve_exit_mach

    mach = _solve_exit_mach(area_ratio, gamma)
    recomputed_ratio = _area_ratio_from_mach(mach, gamma) if mach > 1.0 else 1.0
    rel_error = abs(recomputed_ratio - area_ratio) / area_ratio if area_ratio != 0 else 0.0
    return BenchmarkResult(
        name="mach_area_roundtrip",
        passed=rel_error <= tolerance,
        relative_error=rel_error,
        detail=f"area_ratio_in={area_ratio} -> Mach={mach:.6f} -> area_ratio_recomputed={recomputed_ratio:.6f}",
    )


def run_all_benchmarks(inputs_list: list[dict[str, float]]) -> list[BenchmarkResult]:
    """Corre los 3 benchmarks sobre una lista de casos de entrada representativos."""
    model = ColdGasThrusterPhysicsModel()
    results: list[BenchmarkResult] = []
    for case in inputs_list:
        outputs = model.compute(PhysicsInputs(values=case))
        results.append(check_isp_identity(outputs))
        results.append(
            check_mass_continuity(outputs, gas_constant=case["gas_constant"], throat_area=case["throat_area"])
        )
        results.append(check_mach_area_roundtrip(case["nozzle_exit_area"] / case["throat_area"], case["gas_gamma"]))
    return results
