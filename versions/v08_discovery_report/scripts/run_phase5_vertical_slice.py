#!/usr/bin/env python3
"""
Vertical slice de Phase 5: compara el barrido manual de Phase 4 (grid
sweep) contra la búsqueda matemática real de Optuna — mismo Design Space,
mismo requisito, mismo budget.

Uso:
    python scripts/run_phase5_vertical_slice.py
"""
from __future__ import annotations

from scripts.bootstrap import bootstrap

bootstrap()

from core.design.design_space import DesignSpace  # noqa: E402
from core.design.engine import DesignEngine  # noqa: E402
from core.design.generator import GridSweepGenerator  # noqa: E402
from core.optimization.optuna_backend import OptunaOptimizer  # noqa: E402
from core.orchestrator.budget import Budget  # noqa: E402
from core.requirements.engine import RequirementsEngine  # noqa: E402
from core.requirements.schema import Constraint, Objective, Parameter, ParameterType  # noqa: E402
from infrastructure.logging.structured_logger import configure_logging, get_logger  # noqa: E402


def build_requirements():
    engine = RequirementsEngine()
    return engine.build(
        problem="Maximizar Isp de un thruster de gas frío sujeto a empuje mínimo de 0.8 N",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        constraints=[Constraint(name="min_thrust", expression="thrust >= 0.8", hard=True)],
        variables={
            "chamber_pressure": Parameter(name="chamber_pressure", value=5e5, unit="Pa", type=ParameterType.FIXED),
            "chamber_temperature": Parameter(
                name="chamber_temperature", value=300.0, unit="K", type=ParameterType.FIXED
            ),
            "throat_area": Parameter(name="throat_area", value=1e-6, unit="m^2", type=ParameterType.FIXED),
            "nozzle_exit_area": Parameter(
                name="nozzle_exit_area", value=1e-5, unit="m^2", type=ParameterType.FREE, range=(1e-6, 5e-5)
            ),
            "ambient_pressure": Parameter(name="ambient_pressure", value=0.0, unit="Pa", type=ParameterType.FIXED),
            "gas_gamma": Parameter(name="gas_gamma", value=1.4, unit=None, type=ParameterType.FIXED),
            "gas_constant": Parameter(
                name="gas_constant", value=296.8, unit="J/(kg*K)", type=ParameterType.FIXED
            ),
        },
    )


def main() -> None:
    configure_logging()
    log = get_logger(component="phase5_vertical_slice")

    requirements = build_requirements()
    design_space = DesignSpace.from_requirements(requirements)
    budget = Budget(max_iterations=15, max_simulations=15, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    print(f"\nProblema: {requirements.problem}")
    print(f"Budget: {budget.max_iterations} evaluaciones\n")

    grid_result = DesignEngine().explore(requirements, design_space, GridSweepGenerator(), budget=budget, seed=42)
    best_grid = max(grid_result.valid_designs, key=lambda c: c.results.predictions["specific_impulse"])
    print("--- Phase 4: Grid Sweep (exploracion no dirigida) ---")
    print(f"  Validos: {len(grid_result.valid_designs)}/{grid_result.iterations}")
    print(
        f"  Mejor Isp encontrado: {best_grid.results.predictions['specific_impulse']:.4f}s "
        f"(area={best_grid.design.parameters['nozzle_exit_area'].value:.4e})\n"
    )

    opt_result = OptunaOptimizer().optimize(requirements, design_space, budget=budget, seed=42)
    best_opt = opt_result.best_designs[0]
    print("--- Phase 5: Optuna (busqueda matematica dirigida) ---")
    print(f"  Validos: {sum(1 for e in opt_result.all_evaluations if e.passed)}/{opt_result.iterations}")
    print(
        f"  Mejor Isp encontrado: {best_opt.objective_values['isp']:.4f}s "
        f"(area={best_opt.design.parameters['nozzle_exit_area'].value:.4e})\n"
    )

    log.info(
        "comparison_finished",
        grid_best_isp=best_grid.results.predictions["specific_impulse"],
        optuna_best_isp=best_opt.objective_values["isp"],
    )


if __name__ == "__main__":
    main()
