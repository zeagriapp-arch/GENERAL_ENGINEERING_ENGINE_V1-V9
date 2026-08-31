"""
Numerical Engine — interfaz común para todos los solvers (sección 11/12).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConvergenceStatus(str, Enum):
    CONVERGED = "CONVERGED"
    NOT_CONVERGED = "NOT_CONVERGED"
    DIVERGED = "DIVERGED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class NumericalSolverResult(BaseModel):
    """Sección 13/14/17: toda ejecución numérica reporta esto, sin excepción."""

    values: dict[str, Any] = Field(default_factory=dict)
    convergence_status: ConvergenceStatus = ConvergenceStatus.UNKNOWN
    iterations: int | None = None
    residual: float | None = None
    runtime_seconds: float | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class NumericalSolver(ABC):
    solver_id: str
    name: str
    problem_types: list[str]  # ej. ["ode"], ["nonlinear", "root"]

    @abstractmethod
    def solve(self, problem_spec: dict[str, Any]) -> NumericalSolverResult: ...
