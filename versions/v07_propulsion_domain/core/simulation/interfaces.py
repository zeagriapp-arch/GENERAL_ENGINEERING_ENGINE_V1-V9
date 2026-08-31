"""
Simulation Engine — interfaces (sección 15).

La simulación es independiente del LLM (Principio Fundamental, sección
2): un SimulationSolver toma un Design + PhysicsModel y produce Results
de forma determinista y reproducible.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

from core.design.schema import Design
from core.experiments.schema import Results
from core.physics.interfaces import PhysicsModel


class ParamSpec(BaseModel):
    unit: Optional[str] = None
    description: str = ""


class SimulationSolver(ABC):
    @abstractmethod
    def declare_inputs(self) -> dict[str, ParamSpec]: ...

    @abstractmethod
    def declare_outputs(self) -> dict[str, ParamSpec]: ...

    @abstractmethod
    def run(self, design: Design, *, seed: Optional[int] = None) -> Results:
        """
        Determinista: mismo `design` (+ mismo `seed` si aplica) -> mismo
        `Results` (sección 34, reproducibilidad).
        """
        ...

    @property
    @abstractmethod
    def physics_model(self) -> PhysicsModel: ...
