"""
Optimization Engine — interfaz (sección 16).

"No utilizar LLM como sustituto de algoritmos matemáticos de
optimización." El LLM (Phase 6) podrá sugerir qué variables explorar,
pero la búsqueda matemática la ejecuta siempre este componente.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, ConfigDict

from core.design.design_space import DesignSpace
from core.design.schema import Design
from core.experiments.schema import Results
from core.orchestrator.budget import Budget
from core.requirements.schema import Requirements


class OptimizationCandidate(BaseModel):
    """Un punto evaluado durante la búsqueda — válido o no."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    design: Design
    results: Optional[Results] = None
    passed: bool
    reasons: list[str] = []
    objective_values: dict[str, float] = {}


class OptimizationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    best_designs: list[OptimizationCandidate]  # Pareto front (multi-obj) o mejor único (single-obj)
    all_evaluations: list[OptimizationCandidate]
    iterations: int
    stopping_reason: str


class Optimizer(ABC):
    @abstractmethod
    def optimize(
        self,
        requirements: Requirements,
        design_space: DesignSpace,
        *,
        budget: Budget,
        seed: Optional[int] = None,
    ) -> OptimizationResult: ...
