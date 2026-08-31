"""
Design Agent (Phase 4/6): propone valores para las variables libres del
Design Space. El LLM PROPONE — pero cada valor propuesto se valida
contra los bounds ANTES de construir un Design. Una propuesta fuera de
rango se rechaza aquí mismo, nunca llega al solver.
"""
from __future__ import annotations

from agents.base import Agent
from agents.schemas import DesignProposal
from core.design.design_space import DesignSpace
from core.requirements.schema import Requirements


class DesignProposalRejectedError(ValueError):
    pass


class DesignAgent(Agent):
    name = "design_agent"

    async def propose(self, requirements: Requirements, design_space: DesignSpace) -> dict[str, float]:
        if not design_space.variables:
            return {}

        bounds_desc = "\n".join(
            f"- {name}: [{v.lower_bound}, {v.upper_bound}] {v.unit or ''}".strip()
            for name, v in design_space.variables.items()
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres el Design Agent. Propon UN valor numérico para cada variable libre listada, "
                    "SIEMPRE dentro de sus bounds. No propongas valores para variables fuera de esta lista."
                ),
            },
            {
                "role": "user",
                "content": f"Requisito: {requirements.problem}\n\nVariables libres y bounds:\n{bounds_desc}",
            },
        ]
        proposal = await self.ask(messages, DesignProposal)

        validated: dict[str, float] = {}
        for name, var in design_space.variables.items():
            if name not in proposal.values:
                raise DesignProposalRejectedError(f"El Design Agent no propuso valor para '{name}'.")
            value = proposal.values[name]
            if not var.contains(value):
                raise DesignProposalRejectedError(
                    f"Valor propuesto para '{name}'={value} fuera de bounds "
                    f"[{var.lower_bound}, {var.upper_bound}] — propuesta rechazada."
                )
            validated[name] = value
        return validated
