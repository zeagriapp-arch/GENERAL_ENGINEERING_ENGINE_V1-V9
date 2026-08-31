#!/usr/bin/env python3
"""
Entrypoint del vertical slice de Phase 1.

Ejecuta el ciclo completo Requirements -> Design -> Experiment con los
defaults del Orchestrator (sin PhysicsModel todavía — eso es Phase 3/7
con el cold-gas thruster). El propósito de este script es demostrar que
el sistema es EJECUTABLE de punta a punta y que, sin evidencia física
real, se detiene honestamente en INSUFFICIENT EVIDENCE en vez de
inventar un resultado (Principio Fundamental, sección 2).

Uso:
    python scripts/run_first_experiment.py
"""
from __future__ import annotations

from infrastructure.logging.structured_logger import configure_logging, get_logger
from core.experiments.store import SQLiteExperimentStore
from core.orchestrator.budget import Budget
from core.orchestrator.orchestrator import Orchestrator
from core.requirements.engine import RequirementsEngine
from core.requirements.schema import Objective, Parameter, ParameterType


def build_requirements():
    engine = RequirementsEngine()
    return engine.build(
        problem="Maximizar Isp de un thruster de gas frío dado un límite de masa de propulsante",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        variables={
            "nozzle_exit_area": Parameter(
                name="nozzle_exit_area",
                value=1e-5,
                unit="m^2",
                type=ParameterType.FREE,
                range=(1e-6, 1e-4),
            ),
            "chamber_pressure": Parameter(
                name="chamber_pressure", value=5e5, unit="Pa", type=ParameterType.FIXED
            ),
        },
        operating_conditions={
            "propellant_gas": Parameter(name="propellant_gas", value="N2", unit=None, type=ParameterType.FIXED),
        },
        validation_requirements=["Comparar contra solución analítica de tobera ideal (Phase 3)"],
    )


def main() -> None:
    configure_logging()
    log = get_logger(component="run_first_experiment")

    requirements = build_requirements()
    log.info("requirements_built", problem=requirements.problem)

    store = SQLiteExperimentStore("gede_first_experiment.db")
    orchestrator = Orchestrator(store)
    budget = Budget(
        max_iterations=5,
        max_simulations=10,
        max_llm_calls=10,
        max_runtime_seconds=60,
        max_research_calls=10,
    )

    result = orchestrator.run(requirements, budget=budget)

    log.info(
        "run_finished",
        stopping_reason=result.stopping_reason.value,
        iterations=result.budget_tracker.iterations,
        experiments_saved=len(result.experiment_graph.nodes),
    )

    print("\n--- REPORT (versión mínima — Report Generator completo llega en Phase 8) ---")
    print(f"Problema: {requirements.problem}")
    print(f"Razón de parada: {result.stopping_reason.value}")
    print(f"Iteraciones ejecutadas: {result.budget_tracker.iterations}")
    print(f"Experimentos guardados: {len(result.experiment_graph.nodes)}")
    for note in result.final_state.notes:
        print(f"  - {note}")
    print(f"\nBase de datos de experimentos: gede_first_experiment.db")


if __name__ == "__main__":
    main()
