"""
Optimization Agent (sección 16): "El LLM puede ayudar a decidir 'qué
variables explorar' pero el optimizer realiza la búsqueda matemática."
Este agente NUNCA invoca `run_optimizer` directamente con una decisión
propia — solo sugiere foco; `OptunaOptimizer` (Phase 5) sigue siendo
quien ejecuta la búsqueda real.
"""
from __future__ import annotations

from agents.base import Agent
from agents.schemas import OptimizationFocus
from core.design.design_space import DesignSpace
from core.optimization.interfaces import OptimizationCandidate


class OptimizationAgent(Agent):
    name = "optimization_agent"

    async def suggest_focus(
        self, design_space: DesignSpace, recent_evaluations: list[OptimizationCandidate]
    ) -> OptimizationFocus:
        summary_lines = []
        for ev in recent_evaluations[-5:]:
            values = {k: v.value for k, v in ev.design.parameters.items() if k in design_space.variables}
            summary_lines.append(f"- {values} -> passed={ev.passed} reasons={ev.reasons}")
        summary = "\n".join(summary_lines) if summary_lines else "(sin evaluaciones previas)"

        messages = [
            {
                "role": "system",
                "content": (
                    "Eres el Optimization Agent. Sugiere qué variables priorizar en la próxima ronda de "
                    "búsqueda, dado el historial reciente. NO ejecutas la búsqueda matemática — solo sugieres foco."
                ),
            },
            {
                "role": "user",
                "content": f"Variables disponibles: {list(design_space.variables)}\n\nEvaluaciones recientes:\n{summary}",
            },
        ]
        return await self.ask(messages, OptimizationFocus)
