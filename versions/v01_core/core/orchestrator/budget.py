from __future__ import annotations

import time
from enum import Enum

from pydantic import BaseModel


class StoppingReason(str, Enum):
    CONVERGENCE = "convergence"
    NO_IMPROVEMENT = "no_improvement"
    CONSTRAINT_VIOLATION = "constraint_violation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BUDGET_EXCEEDED = "computational_budget_exceeded"
    STILL_RUNNING = "still_running"


class Budget(BaseModel):
    max_iterations: int
    max_simulations: int
    max_llm_calls: int
    max_runtime_seconds: int
    max_research_calls: int


class BudgetTracker:
    """
    Contabiliza consumo contra un Budget y decide si hay que parar.
    Es la ÚNICA fuente de verdad sobre "¿podemos seguir iterando?" —
    ningún agente ni el LLM puede decidir continuar si el tracker dice
    que no (sección 35: "Nunca permitir loops infinitos").
    """

    def __init__(self, budget: Budget):
        self.budget = budget
        self.iterations = 0
        self.simulations = 0
        self.llm_calls = 0
        self.research_calls = 0
        self._start = time.monotonic()

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start

    def exceeded(self) -> bool:
        return (
            self.iterations >= self.budget.max_iterations
            or self.simulations >= self.budget.max_simulations
            or self.llm_calls >= self.budget.max_llm_calls
            or self.research_calls >= self.budget.max_research_calls
            or self.elapsed_seconds() >= self.budget.max_runtime_seconds
        )

    def record_iteration(self) -> None:
        self.iterations += 1

    def record_simulation(self) -> None:
        self.simulations += 1

    def record_llm_call(self) -> None:
        self.llm_calls += 1

    def record_research_call(self) -> None:
        self.research_calls += 1
