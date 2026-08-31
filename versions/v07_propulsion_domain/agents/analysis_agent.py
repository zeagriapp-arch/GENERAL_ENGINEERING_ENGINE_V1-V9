"""
Analysis Agent (sección 18/38): los DELTAS numéricos se calculan de
forma determinista (nunca los inventa el LLM); el LLM solo agrega una
narrativa en lenguaje natural sobre números ya calculados.
"""
from __future__ import annotations

from typing import Optional

from agents.base import Agent
from agents.schemas import AnalysisNarrative
from core.experiments.schema import EvaluationResult, Results
from core.requirements.schema import Requirements


class AnalysisAgent(Agent):
    name = "analysis_agent"

    def compute_evaluation(
        self, requirements: Requirements, baseline: Optional[Results], candidate: Results
    ) -> EvaluationResult:
        """Determinista — sin LLM. Compara contra el primer objective declarado."""
        if baseline is None or not requirements.objectives:
            return EvaluationResult(improved=None, confidence=candidate.confidence)

        obj = requirements.objectives[0]
        baseline_value = baseline.predictions.get(obj.metric)
        candidate_value = candidate.predictions.get(obj.metric)
        if baseline_value is None or candidate_value is None:
            return EvaluationResult(improved=None, confidence=None)

        delta = candidate_value - baseline_value
        improved = delta > 0 if obj.direction == "maximize" else delta < 0
        confidence = min(baseline.confidence or 0.0, candidate.confidence or 0.0)

        return EvaluationResult(metric_deltas={obj.metric: delta}, improved=improved, confidence=confidence)

    async def narrate(self, requirements: Requirements, evaluation: EvaluationResult) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres el Analysis Agent. Resume en 1-2 frases la comparación dada. "
                    "USA SOLO los números provistos — no inventes ni recalcules ningún valor."
                ),
            },
            {
                "role": "user",
                "content": f"Deltas: {evaluation.metric_deltas} | improved={evaluation.improved} | confidence={evaluation.confidence}",
            },
        ]
        result = await self.ask(messages, AnalysisNarrative)
        return result.narrative
