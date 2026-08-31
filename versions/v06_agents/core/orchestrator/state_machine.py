"""
Máquina de estados del ciclo RESEARCH -> ... -> ITERATE (sección 1).
Deliberadamente simple y explícita (decisión #3 del Architecture Design
Document: Orchestrator custom, no framework externo) para mantener
control total sobre budgets y stopping.
"""
from __future__ import annotations

from enum import Enum


class OrchestratorState(str, Enum):
    RESEARCH = "RESEARCH"
    DESIGN = "DESIGN"
    SIMULATE = "SIMULATE"
    ANALYZE = "ANALYZE"
    CRITIQUE = "CRITIQUE"
    OPTIMIZE = "OPTIMIZE"
    DECIDE = "DECIDE"
    DONE = "DONE"


# Transiciones válidas. DECIDE puede volver a DESIGN (nueva iteración) o ir a DONE.
_VALID_TRANSITIONS: dict[OrchestratorState, set[OrchestratorState]] = {
    OrchestratorState.RESEARCH: {OrchestratorState.DESIGN},
    OrchestratorState.DESIGN: {OrchestratorState.SIMULATE},
    OrchestratorState.SIMULATE: {OrchestratorState.ANALYZE},
    OrchestratorState.ANALYZE: {OrchestratorState.CRITIQUE},
    OrchestratorState.CRITIQUE: {OrchestratorState.OPTIMIZE, OrchestratorState.DECIDE},
    OrchestratorState.OPTIMIZE: {OrchestratorState.DECIDE},
    OrchestratorState.DECIDE: {OrchestratorState.DESIGN, OrchestratorState.DONE},
    OrchestratorState.DONE: set(),
}


class InvalidTransitionError(ValueError):
    pass


def transition(current: OrchestratorState, target: OrchestratorState) -> OrchestratorState:
    if target not in _VALID_TRANSITIONS[current]:
        raise InvalidTransitionError(f"Transición inválida: {current} -> {target}")
    return target
