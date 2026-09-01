"""
Interfaz mínima de integración con `core.design.schema`/`core.design.repository`
(versions/v09_advanced_ai), tal como permite la excepción de la sección 35
("solo deben existir las interfaces necesarias para futuras fases").

Deliberadamente NO conectado a `DesignEngine`/`OptunaOptimizer` — funciones
puras, sin efectos secundarios. Solo opera sobre Designs `LOCKED`, mismo
principio que `requirement_contract.integration`.

Alcance intencionalmente mínimo: traduce `parameters` (los valores
resueltos de las variables) a `core.design.schema.Design.parameters`, que
es lo único que `core.simulation.engine.run()` necesita leer para poder
simular (ver `domains/satellite/propulsion/simulation_adapters/cold_gas_solver.py:run()`,
que solo lee `design.parameters`). Traducir `constraints`/`components`/
`materials` con fidelidad completa queda para cuando exista un caso de uso
real que lo necesite — hacerlo ahora sería adelantar diseño especulativo
(sección 35).
"""
from __future__ import annotations

from core.design.schema import Design as CoreDesign
from core.requirements.schema import Parameter as CoreParameter
from core.requirements.schema import ParameterType as CoreParameterType

from design_contract.schema import Design, DesignStatus


class DesignNotLockedError(ValueError):
    pass


def to_core_design(design: Design, *, domain: str) -> CoreDesign:
    """
    Traduce un `design_contract.Design` LOCKED a `core.design.schema.Design`
    — solo `parameters` (ver docstring del módulo). `domain` debe proveerse
    explícitamente por el caller: `design_contract.Design` es agnóstico de
    dominio por diseño (sección 29) y no tiene ningún campo equivalente a
    `core.design.schema.Design.domain` (que SÍ es específico de dominio,
    ej. "satellite.propulsion").
    """
    if design.status != DesignStatus.LOCKED:
        raise DesignNotLockedError(f"Design {design.id} tiene status={design.status.value}; solo se integran Designs LOCKED.")

    parameters: dict[str, CoreParameter] = {}
    for name, value in {**design.parameters, **design.derived_quantities}.items():
        resolved = value.normalized_value if value.is_normalized else value.original_value
        if isinstance(resolved, list):
            continue  # core.requirements.schema.Parameter no admite valores tipo lista
        parameters[name] = CoreParameter(
            name=name,
            value=resolved,
            unit=value.normalized_unit or value.original_unit,
            type=CoreParameterType.FIXED,
        )

    return CoreDesign(domain=domain, parameters=parameters, provenance=[design.id])
