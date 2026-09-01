"""
Locking y versionado de `Design` (secciones 2, 26).

Mismo patrón exacto que `requirement_contract.versioning`: funciones puras
que nunca mutan, y ese mismo módulo se modeló sobre
`core.design.repository.clone()`/`modify()`. `Design.parent_design_id` es
el linaje de VERSIÓN (D001 v1 -> v2 -> v3) — distinto de `DesignLineage`
(linaje de GENERACIÓN, ver `lineage.py`).
"""
from __future__ import annotations

from typing import Any

from design_contract.schema import Design, DesignStatus, new_id, transition_design_status, utcnow


class DesignLockError(ValueError):
    pass


class DesignRevisionError(ValueError):
    pass


def lock(design: Design) -> Design:
    """Solo desde FEASIBLE. Nunca muta — devuelve una copia."""
    if design.status != DesignStatus.FEASIBLE:
        raise DesignLockError(
            f"Design {design.id} no puede bloquearse: status={design.status.value}, se requiere FEASIBLE."
        )
    new_status = transition_design_status(design.status, DesignStatus.LOCKED)
    return design.model_copy(update={"status": new_status, "updated_at": utcnow()})


def revise(design: Design, changes: dict[str, Any]) -> Design:
    """
    D001 v1 -> D001 v2: produce un Design NUEVO (`id` nuevo,
    `version + 1`, `parent_design_id = design.id`, `status` reiniciado a
    DRAFT). El Design original nunca se modifica.
    """
    protected = {"id", "version", "status", "parent_design_id", "created_at", "updated_at"}
    content_changes = {k: v for k, v in changes.items() if k not in protected}

    data = design.model_dump()
    data.update(content_changes)
    data["id"] = new_id()
    data["version"] = design.version + 1
    data["parent_design_id"] = design.id
    data["status"] = DesignStatus.DRAFT
    data["created_at"] = utcnow()
    data["updated_at"] = utcnow()

    try:
        return Design(**data)
    except Exception as exc:  # noqa: BLE001 — se re-envuelve con contexto, no se oculta
        raise DesignRevisionError(f"No se pudo construir la revisión de {design.id}: {exc}") from exc


def version_chain_ids(design: Design, all_versions: dict[str, Design]) -> list[str]:
    """Cadena de versiones ascendente (más antigua primero) — mismo patrón que requirement_contract.versioning.version_chain_ids."""
    chain: list[str] = []
    current = design.parent_design_id
    seen: set[str] = set()
    while current is not None and current not in seen:
        chain.append(current)
        seen.add(current)
        parent = all_versions.get(current)
        current = parent.parent_design_id if parent else None
    chain.reverse()
    return chain
