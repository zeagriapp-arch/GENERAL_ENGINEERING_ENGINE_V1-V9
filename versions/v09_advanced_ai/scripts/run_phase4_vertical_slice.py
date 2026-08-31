#!/usr/bin/env python3
"""
Vertical slice de Phase 4: dado un requisito con un constraint duro
(empuje mínimo), el Design Engine explora el Design Space del cold-gas
thruster (Phase 3) y devuelve SOLO las configuraciones físicamente
válidas que lo cumplen — con ambas estrategias de generación.

Uso:
    python scripts/run_phase4_vertical_slice.py
"""
from __future__ import annotations

from scripts.bootstrap import bootstrap

bootstrap()

from core.design.design_space import DesignSpace  # noqa: E402
from core.design.engine import DesignEngine  # noqa: E402
from core.design.generator import GridSweepGenerator, RandomSamplingGenerator  # noqa: E402
from core.orchestrator.budget import Budget  # noqa: E402
from core.requirements.engine import RequirementsEngine  # noqa: E402
from core.requirements.schema import Constraint, Objective, Parameter, ParameterType  # noqa: E402
from infrastructure.logging.structured_logger import configure_logging, get_logger  # noqa: E402


def build_requirements():
    engine = RequirementsEngine()
    return engine.build(
        problem="Encontrar áreas de salida de tobera que cumplan empuje mínimo de 0.83 N",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        constraints=[Constraint(name="min_thrust", expression="thrust >= 0.83", hard=True)],
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
    log = get_logger(component="phase4_vertical_slice")

    requirements = build_requirements()
    design_space = DesignSpace.from_requirements(requirements)
    design_engine = DesignEngine()
    budget = Budget(max_iterations=10, max_simulations=10, max_llm_calls=1, max_runtime_seconds=30, max_research_calls=1)

    print(f"\nProblema: {requirements.problem}")
    print(f"Design Space: {list(design_space.variables)} (fixed: {list(design_space.fixed_parameters)})\n")

    for label, generator in [("GRID SWEEP", GridSweepGenerator()), ("RANDOM SAMPLING", RandomSamplingGenerator())]:
        result = design_engine.explore(requirements, design_space, generator, budget=budget, seed=42)
        log.info(
            "exploration_finished",
            strategy=label,
            valid=len(result.valid_designs),
            rejected=len(result.rejected_designs),
            stopping_reason=result.stopping_reason,
        )
        print(f"--- {label} --- ({result.iterations} candidatos evaluados)")
        print(f"  Válidos: {len(result.valid_designs)} | Rechazados: {len(result.rejected_designs)}")
        for c in sorted(result.valid_designs, key=lambda c: c.results.predictions["specific_impulse"], reverse=True)[:3]:
            area = c.design.parameters["nozzle_exit_area"].value
            isp = c.results.predictions["specific_impulse"]
            thrust = c.results.predictions["thrust"]
            print(f"    area={area:.3e} m^2 | Isp={isp:.2f}s | thrust={thrust:.4f}N")
        print()


if __name__ == "__main__":
    main()
