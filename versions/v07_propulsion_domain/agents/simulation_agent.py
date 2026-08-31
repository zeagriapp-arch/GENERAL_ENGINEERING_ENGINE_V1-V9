"""
Simulation Agent (sección 15): NO razona — solo invoca `run_simulation`,
que delega en el Physics/Simulation Engine determinista (Phase 3). Este
agente no usa ModelProvider en absoluto; existe como frontera de
permisos explícita (Tool Registry) y punto de extensión futuro.
"""
from __future__ import annotations

from agents.base import Agent
from core.design.schema import Design
from core.experiments.schema import Results


class SimulationAgentError(ValueError):
    pass


class SimulationAgent(Agent):
    name = "simulation_agent"

    async def simulate(self, design: Design) -> Results:
        result = await self.invoke_tool("run_simulation", {"design": design})
        if not result.ok:
            raise SimulationAgentError(f"run_simulation falló para Design {design.id}: {result.error}")
        return result.value
