"""
Oscilador masa-resorte no amortiguado (sección 36): m*x'' + k*x = 0.

Segundo benchmark genérico — cubre el camino ODE del Numerical Engine
(a diferencia de `constant_acceleration.py`, que es puramente
algebraico). Tiene solución analítica exacta, así que sirve como
benchmark de "Numerical Result vs Analytical Result" (sección 25).
"""
from __future__ import annotations

import math

import numpy as np

from core.design.schema import Design
from core.numerical.ode import ODESolver
from core.numerical.interfaces import ConvergenceStatus
from core.physics.interfaces import PhysicsInputs, PhysicsModel, PhysicsOutputs

REQUIRED_INPUTS = ("mass", "spring_constant", "initial_position", "initial_velocity", "time")


def analytical_solution(mass: float, k: float, x0: float, v0: float, t: float) -> tuple[float, float]:
    """
    Solución cerrada exacta — usada SOLO para construir `expected_outputs`
    de BenchmarkCase (la "respuesta conocida"), nunca dentro de
    `compute()` del modelo (que debe resolver numéricamente vía ODE,
    sección 2: "SOLVER CALCULATES").
    """
    omega = math.sqrt(k / mass)
    x = x0 * math.cos(omega * t) + (v0 / omega) * math.sin(omega * t)
    v = -x0 * omega * math.sin(omega * t) + v0 * math.cos(omega * t)
    return x, v


class MassSpringOscillatorModel(PhysicsModel):
    name = "mass_spring_oscillator_undamped"
    model_id = "benchmark-mass-spring-oscillator"
    description = "Oscilador armónico simple no amortiguado, resuelto vía ODE — benchmark del Numerical Engine."
    version = "1.0"

    validity_range = {
        "mass": (1e-6, 1e6),
        "spring_constant": (1e-6, 1e6),
        "time": (0.0, 1e4),
    }
    required_units = {
        "mass": "kg",
        "spring_constant": "N/m",
        "initial_position": "m",
        "initial_velocity": "m/s",
        "time": "s",
    }

    def __init__(self, ode_solver: ODESolver | None = None):
        self._ode_solver = ode_solver or ODESolver()

    def applies_to(self, design: Design) -> bool:
        return design.domain == "generic.mechanics" and all(
            name in design.parameters for name in REQUIRED_INPUTS
        )

    def assumptions(self) -> list[str]:
        return [
            "Oscilador armónico simple (ley de Hooke, F=-kx)",
            "No amortiguado (sin fricción/disipación)",
            "Masa puntual, resorte ideal sin masa",
        ]

    def compute(self, inputs: PhysicsInputs) -> PhysicsOutputs:
        v = inputs.values
        m, k, x0, v0, t = (
            v["mass"],
            v["spring_constant"],
            v["initial_position"],
            v["initial_velocity"],
            v["time"],
        )

        within_range, notes = self.check_validity({"mass": m, "spring_constant": k, "time": t})

        if not within_range:
            # Sección 10: rechazar ANTES de ejecutar una simulación costosa
            # cuando los inputs ya están fuera de validity_range — no tiene
            # sentido integrar miles de períodos de un ODE solo para
            # confirmar algo que ya sabemos.
            return PhysicsOutputs(
                values={"position": float("nan"), "velocity": float("nan")},
                units={"position": "m", "velocity": "m/s"},
                within_validity_range=False,
                validity_notes=notes + ["Simulación no ejecutada: inputs fuera de validity_range."],
            )

        def rhs(_t: float, y: np.ndarray) -> list[float]:
            x, vel = y
            return [vel, -(k / m) * x]

        sim_result = self._ode_solver.solve(
            {
                "fun": rhs,
                "y0": [x0, v0],
                "t_span": (0.0, t),
                "t_eval": [t],
                "rtol": 1e-10,
                "atol": 1e-12,
            }
        )

        if sim_result.convergence_status != ConvergenceStatus.CONVERGED:
            notes.append(f"ODE solver no convergió: {sim_result.convergence_status.value} — {sim_result.errors}")
            return PhysicsOutputs(
                values={"position": float("nan"), "velocity": float("nan")},
                units={"position": "m", "velocity": "m/s"},
                within_validity_range=False,
                validity_notes=notes,
            )

        position = sim_result.values["y"][0][-1]
        velocity = sim_result.values["y"][1][-1]

        return PhysicsOutputs(
            values={"position": position, "velocity": velocity},
            units={"position": "m", "velocity": "m/s"},
            within_validity_range=within_range,
            validity_notes=notes,
        )
