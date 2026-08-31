#!/usr/bin/env python3
"""
Vertical slice de Phase 7+8: usando el Domain Pack formalizado
(requirements_schema.py), corre Discovery Mode completo y muestra el
Report final — las 12 preguntas de la sección 43 respondidas con datos
reales.

Uso:
    python scripts/run_phase7_8_vertical_slice.py
"""
from __future__ import annotations

from scripts.bootstrap import bootstrap

bootstrap()

from core.design.design_space import DesignSpace  # noqa: E402
from core.experiments.store import SQLiteExperimentStore  # noqa: E402
from core.optimization.optuna_backend import OptunaOptimizer  # noqa: E402
from core.orchestrator.budget import Budget  # noqa: E402
from core.orchestrator.discovery import run_discovery_mode  # noqa: E402
from domains.satellite.propulsion.requirements_schema import build_cold_gas_requirements  # noqa: E402
from infrastructure.logging.structured_logger import configure_logging, get_logger  # noqa: E402


def main() -> None:
    configure_logging()
    log = get_logger(component="phase7_8_vertical_slice")

    requirements = build_cold_gas_requirements(
        "Maximizar Isp de un thruster de gas frío sujeto a empuje mínimo de 0.8 N", min_thrust=0.8
    )
    design_space = DesignSpace.from_requirements(requirements)
    store = SQLiteExperimentStore("gede_phase7_8.db")
    budget = Budget(max_iterations=20, max_simulations=20, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    result = run_discovery_mode(requirements, design_space, OptunaOptimizer(), store, budget=budget, seed=42)

    log.info(
        "discovery_mode_finished",
        total_evaluated=result.total_evaluated,
        total_valid=result.total_valid,
        stopping_reason=result.stopping_reason,
        has_report=result.report is not None,
    )

    print(f"\nCandidatos evaluados: {result.total_evaluated} | válidos: {result.total_valid}\n")

    if result.report is None:
        print("Sin evidencia suficiente: ningún candidato cumplió los requisitos. No se genera Report.")
        return

    print("=" * 70)
    print("REPORT — respondiendo las 12 preguntas de la sección 43")
    print("=" * 70)
    print(result.report.summary_text())


if __name__ == "__main__":
    main()
