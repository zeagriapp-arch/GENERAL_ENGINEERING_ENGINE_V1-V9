"""
Sección 11: los Requirements pueden depender unos de otros
(`R002.dependencies = ["R001"]`). Este módulo da lo mínimo necesario para
que un futuro Requirement Graph completo pueda construirse encima —
verificación de existencia y detección de ciclos — sin implementar todavía
un motor de grafos completo (fuera de alcance de esta fase).
"""
from __future__ import annotations

from requirement_contract.schema import Requirement


def missing_dependencies(requirement: Requirement, known_ids: set[str]) -> list[str]:
    """ids referenciados en `requirement.dependencies` que no existen en `known_ids`."""
    return [dep_id for dep_id in requirement.dependencies if dep_id not in known_ids]


def find_cycles(requirements: list[Requirement]) -> list[list[str]]:
    """
    DFS clásico sobre el grafo dirigido id -> dependencies. Devuelve la
    lista de ciclos encontrados (cada uno como lista de ids en orden,
    cerrando en el primer id repetido) — lista vacía si el grafo es acíclico.
    Requirements cuyas dependencias no existen en `requirements` se ignoran
    aquí (eso es responsabilidad de `missing_dependencies`, no de esta
    función) para no confundir "dependencia faltante" con "ciclo".
    """
    by_id = {r.id: r for r in requirements}
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {r.id: WHITE for r in requirements}
    cycles: list[list[str]] = []

    def visit(node_id: str, path: list[str]) -> None:
        color[node_id] = GRAY
        path.append(node_id)
        for dep_id in by_id[node_id].dependencies:
            if dep_id not in by_id:
                continue  # dependencia inexistente: no es un ciclo, es otro tipo de error
            if color[dep_id] == GRAY:
                cycle_start = path.index(dep_id)
                cycles.append(path[cycle_start:] + [dep_id])
            elif color[dep_id] == WHITE:
                visit(dep_id, path)
        path.pop()
        color[node_id] = BLACK

    for r in requirements:
        if color[r.id] == WHITE:
            visit(r.id, [])

    return cycles
