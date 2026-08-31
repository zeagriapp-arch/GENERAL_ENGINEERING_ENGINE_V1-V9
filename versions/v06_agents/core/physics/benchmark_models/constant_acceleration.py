"""
Movimiento 1-D con aceleración constante (sección 36: "problemas
científicos sencillos y bien conocidos... la intención es verificar el
motor, no demostrar una tecnología espacial").

Vive en `core/physics/benchmark_models/`, NO en `domains/` — es
infraestructura para validar el motor en sí, agnóstica de cualquier
dominio de ingeniería real. Cinemática clásica, forma cerrada exacta:
    x(t) = x0 + v0*t + 0.5*a*t^2
    v(t) = v0 + a*t
"""
from __future__ import annotations

from core.design.schema import Design
from core.physics.interfaces import PhysicsInputs, PhysicsModel, PhysicsOutputs

REQUIRED_INPUTS = ("initial_position", "initial_velocity", "acceleration", "time")


class ConstantAccelerationModel(PhysicsModel):
    name = "constant_acceleration_1d"
    model_id = "benchmark-const-accel-1d"
    description = "Cinemática 1-D con aceleración constante — benchmark algebraico del motor."
    version = "1.0"

    validity_range = {
        "time": (0.0, 1e6),
    }
    required_units = {
        "initial_position": "m",
        "initial_velocity": "m/s",
        "acceleration": "m/s^2",
        "time": "s",
    }
    validation_cases = [
        {
            "known_inputs": {"initial_position": 0.0, "initial_velocity": 0.0, "acceleration": 9.8, "time": 2.0},
            "expected_outputs": {"position": 19.6, "velocity": 19.6},
        }
    ]

    def applies_to(self, design: Design) -> bool:
        return design.domain == "generic.mechanics" and all(
            name in design.parameters for name in REQUIRED_INPUTS
        )

    def assumptions(self) -> list[str]:
        return ["Movimiento 1-D", "Aceleración constante en el tiempo", "Sin fricción/resistencia"]

    def compute(self, inputs: PhysicsInputs) -> PhysicsOutputs:
        v = inputs.values
        x0, v0, a, t = v["initial_position"], v["initial_velocity"], v["acceleration"], v["time"]

        position = x0 + v0 * t + 0.5 * a * t**2
        velocity = v0 + a * t

        within_range, notes = self.check_validity({"time": t})

        return PhysicsOutputs(
            values={"position": position, "velocity": velocity},
            units={"position": "m", "velocity": "m/s"},
            within_validity_range=within_range,
            validity_notes=notes,
        )
