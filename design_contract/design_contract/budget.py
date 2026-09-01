"""
`ExperimentBudget` (sección 25) — solo se crea porque encaja de forma
natural y barata en la arquitectura (regla explícita de la sección 25:
"no implementar todavía el scheduler; solo crear una abstracción si
encaja naturalmente").

Distinto de `core.orchestrator.budget.Budget` (v09_advanced_ai): ese
gobierna el loop del Orchestrator (iteraciones, llamadas a LLM, tiempo de
ejecución del CICLO completo research->design->simulate->critique). Este
gobierna específicamente la exploración de un DesignSpace (cuántos
candidatos generar, cuántas simulaciones, cuánto cómputo/costo) — un
ámbito más acotado, con campos que `Budget` no tiene (`max_candidates`,
`max_cost`) y sin los que le son ajenos (`max_llm_calls`,
`max_research_calls`). No se reutiliza `Budget` tal cual porque el
conjunto de campos es genuinamente distinto, no un simple renombrado.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ExperimentBudget(BaseModel):
    max_candidates: Optional[int] = None
    max_simulations: Optional[int] = None
    max_compute_time_seconds: Optional[float] = None
    max_cost: Optional[float] = None
    max_iterations: Optional[int] = None

    def exceeded_by(self, *, candidates: int = 0, simulations: int = 0, elapsed_seconds: float = 0.0, cost: float = 0.0, iterations: int = 0) -> bool:
        checks = [
            (self.max_candidates, candidates),
            (self.max_simulations, simulations),
            (self.max_compute_time_seconds, elapsed_seconds),
            (self.max_cost, cost),
            (self.max_iterations, iterations),
        ]
        return any(limit is not None and actual >= limit for limit, actual in checks)
