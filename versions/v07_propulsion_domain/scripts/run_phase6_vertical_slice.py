#!/usr/bin/env python3
"""
Vertical slice de Phase 6: ciclo completo con los 6 agentes reales sobre
un ModelProvider guionizado (sin Ollama disponible en este entorno) +
física real del cold-gas thruster (Phase 3).

Uso:
    python scripts/run_phase6_vertical_slice.py
"""
from __future__ import annotations

import asyncio
import json

from scripts.bootstrap import bootstrap

bootstrap()

from agents.orchestrator import AsyncOrchestrator  # noqa: E402
from config.settings import get_settings  # noqa: E402
from core.design.design_space import DesignSpace  # noqa: E402
from core.experiments.store import SQLiteExperimentStore  # noqa: E402
from core.models.interfaces import ModelProvider, ModelResponse  # noqa: E402
from core.models.registry import ModelRegistry  # noqa: E402
from core.orchestrator.budget import Budget  # noqa: E402
from core.requirements.engine import RequirementsEngine  # noqa: E402
from core.requirements.schema import Constraint, Objective, Parameter, ParameterType  # noqa: E402
from core.tools.registry import ToolRegistry  # noqa: E402
from infrastructure.logging.structured_logger import configure_logging, get_logger  # noqa: E402


class ScriptedModelProvider(ModelProvider):
    """Sustituto de Ollama para este entorno sin servidor real disponible."""

    def __init__(self, responses: dict[str, list[dict]]):
        self._responses = {k: list(v) for k, v in responses.items()}

    async def complete(self, messages, *, role="reasoning", response_schema=None, tools=None):
        structured = self._responses[role].pop(0)
        return ModelResponse(text=json.dumps(structured), structured=structured, tool_calls=[], raw={})

    async def embed(self, texts, *, role="embeddings"):
        raise NotImplementedError


def build_requirements():
    engine = RequirementsEngine()
    return engine.build(
        problem="Maximizar Isp de un thruster de gas frío sujeto a empuje mínimo",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        constraints=[Constraint(name="min_thrust", expression="thrust >= 0.5", hard=True)],
        variables={
            "chamber_pressure": Parameter(name="chamber_pressure", value=5e5, unit="Pa", type=ParameterType.FIXED),
            "chamber_temperature": Parameter(name="chamber_temperature", value=300.0, unit="K", type=ParameterType.FIXED),
            "throat_area": Parameter(name="throat_area", value=1e-6, unit="m^2", type=ParameterType.FIXED),
            "nozzle_exit_area": Parameter(
                name="nozzle_exit_area", value=1e-5, unit="m^2", type=ParameterType.FREE, range=(1e-6, 5e-5)
            ),
            "ambient_pressure": Parameter(name="ambient_pressure", value=0.0, unit="Pa", type=ParameterType.FIXED),
            "gas_gamma": Parameter(name="gas_gamma", value=1.4, unit=None, type=ParameterType.FIXED),
            "gas_constant": Parameter(name="gas_constant", value=296.8, unit="J/(kg*K)", type=ParameterType.FIXED),
        },
    )


async def main() -> None:
    configure_logging()
    log = get_logger(component="phase6_vertical_slice")

    provider = ScriptedModelProvider(
        {
            "reasoning": [
                {"relevant_equations": ["eq-thrust-general"], "notes": ["contexto ok"], "open_questions": []},
                {"values": {"nozzle_exit_area": 2e-5}, "rationale": "primer intento, valor medio del rango"},
                {"findings": [], "risk_level": "LOW"},
            ]
        }
    )
    model_registry = ModelRegistry(get_settings(), provider)
    tool_registry = ToolRegistry(get_settings().tools)
    store = SQLiteExperimentStore("gede_phase6.db")

    requirements = build_requirements()
    design_space = DesignSpace.from_requirements(requirements)
    orchestrator = AsyncOrchestrator(store, model_registry, tool_registry)
    budget = Budget(max_iterations=1, max_simulations=5, max_llm_calls=20, max_runtime_seconds=30, max_research_calls=5)

    result = await orchestrator.run(requirements, design_space, budget=budget)

    log.info("run_finished", stopping_reason=result.stopping_reason.value, experiments=len(result.experiment_graph.nodes))
    print(f"\nRazón de parada: {result.stopping_reason.value}")
    print(f"Experimentos guardados: {len(result.experiment_graph.nodes)}")
    for note in result.final_state.notes:
        print(f"  - {note}")


if __name__ == "__main__":
    asyncio.run(main())
