"""
SimulationSolver del cold-gas thruster: extrae parámetros de un Design,
llama al PhysicsModel, y construye `Results` con confidence/model_validity
(Uncertainty Engine básico — la propagación estadística completa,
Monte Carlo, etc. llegan en Phase 9).
"""
from __future__ import annotations

from typing import Optional

from core.design.schema import Design
from core.experiments.schema import Results
from core.physics.interfaces import PhysicsInputs, PhysicsModel
from core.simulation.interfaces import ParamSpec, SimulationSolver
from domains.satellite.propulsion.physics_models.cold_gas_thruster import (
    ColdGasThrusterPhysicsModel,
    REQUIRED_INPUTS,
)


class ColdGasParameterMissingError(ValueError):
    pass


class ColdGasNozzleSolver(SimulationSolver):
    def __init__(self, model: Optional[PhysicsModel] = None):
        self._model = model or ColdGasThrusterPhysicsModel()

    @property
    def physics_model(self) -> PhysicsModel:
        return self._model

    def declare_inputs(self) -> dict[str, ParamSpec]:
        return {name: ParamSpec(unit=self._model.required_units.get(name)) for name in REQUIRED_INPUTS}

    def declare_outputs(self) -> dict[str, ParamSpec]:
        return {
            "thrust": ParamSpec(unit="N", description="Empuje"),
            "specific_impulse": ParamSpec(unit="s", description="Impulso específico"),
            "mass_flow_rate": ParamSpec(unit="kg/s", description="Flujo másico"),
            "exit_velocity": ParamSpec(unit="m/s", description="Velocidad de salida"),
            "exit_mach": ParamSpec(unit=None, description="Número de Mach de salida"),
            "characteristic_velocity": ParamSpec(unit="m/s", description="Velocidad característica c*"),
            "thrust_coefficient": ParamSpec(unit=None, description="Coeficiente de empuje CF"),
        }

    def run(self, design: Design, *, seed: Optional[int] = None) -> Results:
        # determinista: no hay aleatoriedad en este modelo, `seed` se
        # ignora deliberadamente (documentado — sección 34: reproducible
        # por construcción, no por control de semilla).
        missing = [name for name in REQUIRED_INPUTS if name not in design.parameters]
        if missing:
            raise ColdGasParameterMissingError(
                f"Design {design.id} no tiene los parámetros requeridos: {missing}"
            )

        values = {}
        for name in REQUIRED_INPUTS:
            param = design.parameters[name]
            if not isinstance(param.value, (int, float)):
                raise ColdGasParameterMissingError(f"Parámetro '{name}' no es numérico: {param.value!r}")
            values[name] = float(param.value)

        outputs = self._model.compute(PhysicsInputs(values=values))

        confidence = 0.9 if outputs.within_validity_range else 0.3
        model_validity = "within_range" if outputs.within_validity_range else "out_of_range"

        return Results(
            predictions=outputs.values,
            units=outputs.units,
            confidence=confidence,
            uncertainty=None,  # propagación cuantitativa: Phase 9 (Scientific ML / Monte Carlo)
            model_validity=model_validity,
            data_quality="high",  # ecuaciones curadas de fuente pública verificable (Phase 2)
        )
