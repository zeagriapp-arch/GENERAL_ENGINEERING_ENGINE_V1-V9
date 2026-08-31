"""
Critic Agent (sección 19/38): "El LLM NO debe... declarar validación sin
ejecutar validadores... modificar resultados... saltarse constraints."

Por eso: el veredicto ACCEPT/REJECT se calcula SIEMPRE con la misma
regla determinista que usan Design Engine y Optimizer
(`core.design.candidate.evaluate_requirements`), ANTES de preguntarle
nada al LLM. El LLM solo puede añadir hallazgos cualitativos adicionales
al mismo veredicto — nunca cambiarlo.
"""
from __future__ import annotations

from agents.base import Agent
from agents.schemas import CriticFindings
from core.design.candidate import evaluate_requirements
from core.design.schema import Design
from core.experiments.schema import Results, Verdict
from core.requirements.schema import Requirements


class CriticAgent(Agent):
    name = "critic_agent"

    def _deterministic_verdict(self, requirements: Requirements, results: Results) -> tuple[str, list[str]]:
        passed, reasons = evaluate_requirements(requirements, results)
        return ("ACCEPT" if passed else "REJECT"), reasons

    async def critique(self, requirements: Requirements, design: Design, results: Results) -> Verdict:
        decision, deterministic_reasons = self._deterministic_verdict(requirements, results)

        messages = [
            {
                "role": "system",
                "content": (
                    "Eres el Critic Agent. Busca supuestos cuestionables, dependencias excesivas en datos "
                    "inciertos, o inconsistencias adicionales en los resultados. NO puedes cambiar la "
                    "decisión ACCEPT/REJECT — esa ya fue calculada; solo puedes añadir hallazgos cualitativos."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Resultados: {results.predictions} | model_validity={results.model_validity} | "
                    f"confidence={results.confidence} | decisión ya calculada: {decision}"
                ),
            },
        ]
        llm_findings = await self.ask(messages, CriticFindings)

        all_findings = deterministic_reasons + [f"[LLM, risk={llm_findings.risk_level}] {f}" for f in llm_findings.findings]
        return Verdict(decision=decision, findings=all_findings)
