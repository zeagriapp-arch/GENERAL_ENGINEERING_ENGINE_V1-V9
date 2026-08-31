"""
Simulation Engine (sección 15): Design -> Model -> Solver -> Results.

IMPORTANTE: este módulo NUNCA importa nada de `domains/` (regla core ↛
domains). El mapeo domain -> SimulationSolver concreto se registra desde
fuera (scripts/bootstrap.py), que sí puede importar domains. Esto es lo
que permite que `run_simulation` (tool en config/tools.yaml) apunte a
una función libre de este módulo sin romper el import boundary.

Si no hay solver registrado para el domain de un Design, se devuelve
`Results` explícitamente UNKNOWN — nunca se inventa un resultado
(Principio Fundamental, sección 2), consistente con el default de
Orchestrator en Phase 1.
"""
from __future__ import annotations

from typing import Optional

from core.design.schema import Design
from core.experiments.schema import Results
from core.simulation.interfaces import SimulationSolver

_registry: dict[str, SimulationSolver] = {}


def register_solver(domain: str, solver: SimulationSolver) -> None:
    _registry[domain] = solver


def unregister_all() -> None:
    """Solo para tests — limpia el registro global entre casos."""
    _registry.clear()


def get_solver(domain: str) -> Optional[SimulationSolver]:
    return _registry.get(domain)


def run(design: Design, *, seed: Optional[int] = None) -> Results:
    """Tool: run_simulation."""
    solver = _registry.get(design.domain)
    if solver is None:
        return Results(
            model_validity="unknown",
            data_quality="unknown",
            confidence=None,
        )
    return solver.run(design, seed=seed)
