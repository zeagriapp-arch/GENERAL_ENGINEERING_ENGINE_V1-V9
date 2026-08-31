"""
Requirements/Parameter schema del dominio satellite.propulsion (sección
29). Consolida lo que hasta ahora estaba duplicado en 4 scripts de demo
(Phase 3-6) — un solo lugar que define qué parámetros necesita el
cold-gas thruster y con qué defaults/unidades.

NO reemplaza `core.requirements.schema.Requirements` (el Core sigue sin
saber nada de propulsión) — esto es azúcar sintáctico específico del
dominio que construye un `Requirements` válido.
"""
from __future__ import annotations

from core.requirements.schema import Constraint, Objective, Parameter, ParameterType, Requirements

DOMAIN = "satellite.propulsion"

# Valores por defecto razonables para un thruster de N2 de referencia
# (usados en todos los vertical slices de Phase 3-6).
DEFAULT_FIXED_PARAMETERS = {
    "chamber_pressure": (5e5, "Pa"),  # 5 bar
    "chamber_temperature": (300.0, "K"),
    "throat_area": (1e-6, "m^2"),
    "ambient_pressure": (0.0, "Pa"),  # vacío
    "gas_gamma": (1.4, None),  # N2
    "gas_constant": (296.8, "J/(kg*K)"),  # N2
}

DEFAULT_EXIT_AREA_RANGE = (1e-6, 5e-5)  # m^2 — area_ratio 1 a 50 dado throat_area por defecto


def build_cold_gas_requirements(
    problem: str,
    *,
    objective_metric: str = "specific_impulse",
    objective_direction: str = "maximize",
    min_thrust: float | None = None,
    exit_area_range: tuple[float, float] = DEFAULT_EXIT_AREA_RANGE,
    fixed_overrides: dict[str, float] | None = None,
) -> Requirements:
    """
    Construye un Requirements válido para el cold-gas thruster sin
    repetir los 7 parámetros en cada script. `fixed_overrides` permite
    cambiar cualquier default (ej. otro gas, otra presión de cámara)
    sin tocar esta función.
    """
    fixed_overrides = fixed_overrides or {}
    variables: dict[str, Parameter] = {}
    for name, (value, unit) in DEFAULT_FIXED_PARAMETERS.items():
        variables[name] = Parameter(
            name=name, value=fixed_overrides.get(name, value), unit=unit, type=ParameterType.FIXED
        )
    variables["nozzle_exit_area"] = Parameter(
        name="nozzle_exit_area",
        value=exit_area_range[0],
        unit="m^2",
        type=ParameterType.FREE,
        range=exit_area_range,
    )

    constraints = []
    if min_thrust is not None:
        constraints.append(Constraint(name="min_thrust", expression=f"thrust >= {min_thrust}", hard=True))

    return Requirements(
        problem=problem,
        domain=DOMAIN,
        objectives=[Objective(name=objective_metric, direction=objective_direction, metric=objective_metric)],
        constraints=constraints,
        variables=variables,
    )
