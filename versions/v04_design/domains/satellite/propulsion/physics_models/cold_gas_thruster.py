"""
PhysicsModel del cold-gas thruster (tobera ideal, flujo isentrópico
1-D). Implementa exactamente las ecuaciones curadas en
domains/satellite/propulsion/knowledge/seed_knowledge.py — mismo
nombre de ecuación (`eq-*`), misma fuente (NASA Glenn Research Center /
Wikipedia). Si alguna vez cambian las ecuaciones curadas, este archivo
debe revisarse en conjunto (son la misma física, en dos representaciones
distintas: conocimiento consultable vs. código ejecutable).
"""
from __future__ import annotations

import math

from core.design.schema import Design
from core.numerical.root_finding import RootNotBracketedError, solve_scalar_root
from core.physics.interfaces import PhysicsInputs, PhysicsModel, PhysicsOutputs

G0 = 9.80665  # m/s^2 — gravedad estándar (eq-specific-impulse, ExtractedFact curado)

REQUIRED_INPUTS = (
    "chamber_pressure",  # pt [Pa]
    "chamber_temperature",  # Tt [K]
    "throat_area",  # At [m^2]
    "nozzle_exit_area",  # Ae [m^2]
    "ambient_pressure",  # p0 [Pa]
    "gas_gamma",  # razón de calores específicos [-]
    "gas_constant",  # R [J/(kg*K)]
)


def _area_ratio_from_mach(mach: float, gamma: float) -> float:
    """eq-exit-pressure-ratio / relación área-Mach isentrópica (doc-isentropic-exit-relations)."""
    term = (2.0 / (gamma + 1.0)) * (1.0 + (gamma - 1.0) / 2.0 * mach**2)
    exponent = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    return (1.0 / mach) * term**exponent


def _solve_exit_mach(area_ratio: float, gamma: float) -> float:
    """
    Rama supersónica (M > 1) de la relación área-Mach — es la que
    corresponde a una tobera convergente-divergente diseñada para
    acelerar el flujo (doc-nozzle-design-qualitative).
    """
    if area_ratio <= 1.0 + 1e-9:
        return 1.0  # sin sección divergente: M=1 en la salida (garganta = salida)

    def f(mach: float) -> float:
        return _area_ratio_from_mach(mach, gamma) - area_ratio

    try:
        result = solve_scalar_root(f, bracket=(1.0 + 1e-9, 200.0))
    except RootNotBracketedError as exc:
        raise ValueError(
            f"No se pudo resolver Mach de salida para area_ratio={area_ratio}: {exc}"
        ) from exc
    return result.root


class ColdGasThrusterPhysicsModel(PhysicsModel):
    name = "cold_gas_thruster_ideal_nozzle"

    # Rangos de validez declarados explícitamente (sección 13). Fuera de
    # este rango, `compute()` sigue calculando pero marca
    # `within_validity_range=False` — nunca falla silenciosamente.
    validity_range = {
        "area_ratio": (1.0, 500.0),
        "chamber_pressure": (1e3, 5e7),  # 1 kPa a 50 MPa
        "chamber_temperature": (50.0, 2000.0),  # K
        "gas_gamma": (1.05, 1.8),
    }

    required_units = {
        "chamber_pressure": "Pa",
        "chamber_temperature": "K",
        "throat_area": "m^2",
        "nozzle_exit_area": "m^2",
        "ambient_pressure": "Pa",
        "gas_gamma": "",
        "gas_constant": "J/(kg*K)",
    }

    def applies_to(self, design: Design) -> bool:
        if design.domain != "satellite.propulsion":
            return False
        return all(name in design.parameters for name in REQUIRED_INPUTS)

    def assumptions(self) -> list[str]:
        # Consolidado de las 6 ecuaciones curadas (Phase 2 knowledge base).
        return [
            "Flujo 1-D estacionario (eq-thrust-general, eq-choked-mass-flow)",
            "Gas ideal, sin fricción/pérdidas — flujo isentrópico (doc-isentropic-exit-relations)",
            "Mach = 1 exactamente en la garganta — flujo atorado (eq-choked-mass-flow)",
            "No hay ondas de choque dentro de la tobera",
            "No hay ingesta de aire externo (eq-thrust-general)",
            "g0 = 9.80665 m/s^2 para Isp (eq-specific-impulse)",
        ]

    def compute(self, inputs: PhysicsInputs) -> PhysicsOutputs:
        v = inputs.values
        pt, Tt, At, Ae, p0, gamma, R = (
            v["chamber_pressure"],
            v["chamber_temperature"],
            v["throat_area"],
            v["nozzle_exit_area"],
            v["ambient_pressure"],
            v["gas_gamma"],
            v["gas_constant"],
        )

        area_ratio = Ae / At
        Me = _solve_exit_mach(area_ratio, gamma)

        # eq-exit-pressure-ratio (doc-isentropic-exit-relations)
        pe_over_pt = (1.0 + (gamma - 1.0) / 2.0 * Me**2) ** (-gamma / (gamma - 1.0))
        Te_over_Tt = (1.0 + (gamma - 1.0) / 2.0 * Me**2) ** -1.0
        pe = pt * pe_over_pt
        Te = Tt * Te_over_Tt

        Ve = Me * math.sqrt(gamma * R * Te)

        # eq-choked-mass-flow
        mdot = (
            (At * pt / math.sqrt(Tt))
            * math.sqrt(gamma / R)
            * ((gamma + 1.0) / 2.0) ** (-(gamma + 1.0) / (2.0 * (gamma - 1.0)))
        )

        # eq-thrust-general
        F = mdot * Ve + (pe - p0) * Ae
        # eq-specific-impulse
        Isp = F / (mdot * G0) if mdot > 0 else 0.0
        # eq-characteristic-velocity / eq-thrust-coefficient
        c_star = pt * At / mdot if mdot > 0 else 0.0
        CF = F / (pt * At) if pt > 0 and At > 0 else 0.0

        check_values = {"area_ratio": area_ratio, "chamber_pressure": pt, "chamber_temperature": Tt, "gas_gamma": gamma}
        within_range, notes = self.check_validity(check_values)
        if Me < 1.0 - 1e-6:
            within_range = False
            notes.append(f"Mach de salida calculado ({Me:.4f}) < 1: viola supuesto de flujo atorado.")
        if pt <= p0:
            within_range = False
            notes.append(f"chamber_pressure ({pt}) <= ambient_pressure ({p0}): no hay flujo neto hacia afuera.")

        return PhysicsOutputs(
            values={
                "thrust": F,
                "specific_impulse": Isp,
                "mass_flow_rate": mdot,
                "exit_velocity": Ve,
                "exit_mach": Me,
                "exit_pressure": pe,
                "exit_temperature": Te,
                "characteristic_velocity": c_star,
                "thrust_coefficient": CF,
                "area_ratio": area_ratio,
            },
            units={
                "thrust": "N",
                "specific_impulse": "s",
                "mass_flow_rate": "kg/s",
                "exit_velocity": "m/s",
                "exit_mach": "",
                "exit_pressure": "Pa",
                "exit_temperature": "K",
                "characteristic_velocity": "m/s",
                "thrust_coefficient": "",
                "area_ratio": "",
            },
            within_validity_range=within_range,
            validity_notes=notes,
        )
