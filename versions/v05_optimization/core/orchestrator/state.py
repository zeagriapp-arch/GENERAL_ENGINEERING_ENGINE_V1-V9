"""
ProjectState: el ÚNICO estado compartido entre todos los agentes
(sección 6 — "NO crear memorias aisladas e incompatibles entre
agentes"). Cada agente lee el estado completo; el Orchestrator es el
único que lo muta entre transiciones de estado.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from core.design.schema import Design
from core.experiments.schema import Experiment
from core.requirements.schema import Requirements


class ProjectState(BaseModel):
    requirements: Requirements
    baseline_design: Optional[Design] = None
    current_design: Optional[Design] = None
    current_experiment_id: Optional[str] = None
    experiment_history: list[str] = Field(default_factory=list)  # ids en orden de creación
    iteration: int = 0
    notes: list[str] = Field(default_factory=list)  # trazas legibles para el Report (Phase 8)

    def record_note(self, note: str) -> None:
        self.notes.append(note)
