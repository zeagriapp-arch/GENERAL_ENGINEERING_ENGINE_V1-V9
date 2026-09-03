"""
Locking y versionado (secciones 12, 16).

Modelado deliberadamente sobre `core.design.repository.clone()`/`modify()`
(versions/v09_advanced_ai): funciones puras que nunca mutan el objeto de
entrada, siempre devuelven uno nuevo. Es el mismo principio que ya usa el
resto del proyecto para lograr inmutabilidad efectiva sin necesitar
`model_config = ConfigDict(frozen=True)` en el schema — la disciplina está
en estas funciones, no en el tipo.

Un Requirement LOCKED nunca se modifica "en el lugar": `revise()` es la
ÚNICA vía sancionada para cambiarlo, y siempre produce una nueva versión
con su propio id, enlazada por `previous_version_id` — igual que
`Design.parent_id` preserva el linaje de un diseño clonado.
"""
from __future__ import annotations

from typing import Any

from requirement_contract.schema import Requirement, RequirementStatus, new_id, transition_status, utcnow


class RequirementLockError(ValueError):
    pass


class RequirementRevisionError(ValueError):
    pass


def lock(requirement: Requirement) -> Requirement:
    """
    Bloquea un Requirement ya VALIDATED. No muta `requirement` — devuelve
    una copia con `status=LOCKED`. Un Requirement solo puede bloquearse
    desde VALIDATED (ver `VALID_STATUS_TRANSITIONS`) — nunca desde DRAFT,
    INVALID, CONFLICTING ni BLOCKED.
    """
    if requirement.status != RequirementStatus.VALIDATED:
        raise RequirementLockError(
            f"Requirement {requirement.id} no puede bloquearse: status={requirement.status.value}, "
            f"se requiere VALIDATED. Corre la validation pipeline primero."
        )
    new_status = transition_status(requirement.status, RequirementStatus.LOCKED)
    return requirement.model_copy(update={"status": new_status, "updated_at": utcnow()})


def revise(requirement: Requirement, changes: dict[str, Any]) -> Requirement:
    """
    Sección 16: "no sobrescribir silenciosamente". Produce un Requirement
    NUEVO (nuevo id, `version = requirement.version + 1`,
    `previous_version_id = requirement.id`, `status` reiniciado a DRAFT —
    una revisión siempre debe volver a pasar por la validation pipeline
    completa, nunca hereda un status VALIDATED/LOCKED del padre). El
    Requirement original NUNCA se modifica ni se elimina — queda accesible
    tal cual para reconstruir el historial (`R001 v1`, `R001 v2`, ...).

    `changes` solo puede tocar campos de contenido (subject, parameter,
    type, operator, value, priority, uncertainty, validity, dependencies,
    provenance, metadata) — intentar cambiar id/version/status/
    previous_version_id/created_at directamente se ignora (esos campos los
    controla exclusivamente esta función).
    """
    protected = {"id", "version", "status", "previous_version_id", "created_at", "updated_at", "confidence", "verification"}
    content_changes = {k: v for k, v in changes.items() if k not in protected}

    data = requirement.model_dump()
    data.update(content_changes)
    data["id"] = new_id()
    data["version"] = requirement.version + 1
    data["previous_version_id"] = requirement.id
    data["status"] = RequirementStatus.DRAFT
    data["created_at"] = utcnow()
    data["updated_at"] = utcnow()
    # Una revisión de contenido invalida cualquier confidence/verification
    # previa — deben recalcularse contra el nuevo contenido, nunca
    # heredarse (sección 8: verification nunca se hereda por afirmación).
    data["confidence"] = {}
    data["verification"] = {}

    try:
        return Requirement(**data)
    except Exception as exc:  # noqa: BLE001 — se re-envuelve con contexto, no se oculta
        raise RequirementRevisionError(f"No se pudo construir la revisión de {requirement.id}: {exc}") from exc


def version_chain_ids(requirement: Requirement, all_versions: dict[str, Requirement]) -> list[str]:
    """
    Reconstruye la cadena de versiones ascendente (más antigua primero)
    dado un mapa {id: Requirement} con todas las versiones conocidas —
    equivalente a `core.orchestrator.report._ancestry_chain` pero para
    Requirements en vez de Experiments.
    """
    chain: list[str] = []
    current = requirement.previous_version_id
    seen: set[str] = set()
    while current is not None and current not in seen:
        chain.append(current)
        seen.add(current)
        parent = all_versions.get(current)
        current = parent.previous_version_id if parent else None
    chain.reverse()
    return chain
