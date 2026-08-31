"""
Operaciones sobre `Design` (sección 11): crear, clonar, modificar,
comparar. El versionado/persistencia real vive dentro de `Experiment`
(Experiment Memory), porque un Design solo tiene sentido de negocio
ligado al experimento que lo produjo — pero estas funciones son puras y
no dependen de ExperimentStore, así que se pueden usar libremente desde
Design Agent / Optimization Agent.

Funciones expuestas como tools en config/tools.yaml:
create, modify, compare.
"""
from __future__ import annotations

from typing import Any

from core.design.schema import Design
from core.requirements.schema import Parameter, ParameterType


class DesignModificationError(ValueError):
    pass


def create(domain: str, **kwargs: Any) -> Design:
    """Tool: create_design."""
    return Design(domain=domain, **kwargs)


def clone(design: Design, *, as_child: bool = True) -> Design:
    """
    Clona un Design. Si `as_child`, el clon queda enlazado como hijo
    (parent_id) — es lo normal al generar una variante para explorar.
    """
    data = design.model_dump(exclude={"id", "created_at"})
    new = Design(**data)
    if as_child:
        new.parent_id = design.id
    return new


def modify(design: Design, changes: dict[str, float | int | str]) -> Design:
    """
    Tool: modify_design.

    Aplica cambios SOLO sobre variables `free` o `constrained` (sección 12
    — "el optimizer solamente puede modificar variables autorizadas").
    Devuelve un nuevo Design (no muta el original — inmutabilidad para
    trazabilidad del Experiment Graph).
    """
    new = clone(design, as_child=True)
    for name, value in changes.items():
        if name not in new.parameters:
            raise DesignModificationError(
                f"No se puede modificar '{name}': no existe en Design {design.id}."
            )
        param = new.parameters[name]
        if param.type not in (ParameterType.FREE, ParameterType.CONSTRAINED):
            raise DesignModificationError(
                f"No se puede modificar '{name}': es tipo '{param.type.value}', "
                f"solo FREE/CONSTRAINED son modificables por el optimizer."
            )
        if param.range is not None and not (param.range[0] <= value <= param.range[1]):
            raise DesignModificationError(
                f"Valor {value} para '{name}' fuera de range {param.range}."
            )
        new.parameters[name] = param.model_copy(update={"value": value})
    return new


def compare(a: Design, b: Design) -> dict[str, dict[str, Any]]:
    """
    Tool: compare_designs. Diff estructural a nivel de `parameters`.
    Devuelve {param_name: {"a": valor, "b": valor}} solo para los que
    difieren o existen en uno y no en el otro.
    """
    diff: dict[str, dict[str, Any]] = {}
    all_names = set(a.parameters) | set(b.parameters)
    for name in all_names:
        pa = a.parameters.get(name)
        pb = b.parameters.get(name)
        va = pa.value if pa else None
        vb = pb.value if pb else None
        if va != vb:
            diff[name] = {"a": va, "b": vb}
    return diff
