#!/usr/bin/env python3
"""
Vertical slice de Phase 3: ciclo completo Requirements -> Design ->
SIMULATION REAL (cold-gas thruster) -> Evaluation -> Critique ->
Experiment Storage, con el PhysicsModel/SimulationSolver de esta fase.

El barrido de `nozzle_exit_area` es manual aquí (una lista fija) porque
el Optimizer real (búsqueda matemática vía Optuna) es Phase 5 — este
script demuestra que el pipeline completo ya es ejecutable con física
real, no que ya optimiza automáticamente.

Uso:
    python scripts/run_phase3_vertical_slice.py
"""
from __future__ import annotations

from scripts.bootstrap import bootstrap

bootstrap()

from core.design.repository import clone, create, modify  # noqa: E402
from core.experiments.schema import EvaluationResult, Results, Verdict  # noqa: E402
from core.experiments.store import SQLiteExperimentStore  # noqa: E402
from core.orchestrator.budget import Budget  # noqa: E402
from core.orchestrator.orchestrator import Orchestrator  # noqa: E402
from core.orchestrator.state import ProjectState  # noqa: E402
from core.requirements.engine import RequirementsEngine  # noqa: E402
from core.requirements.schema import Objective, Parameter, ParameterType  # noqa: E402
from core.simulation import engine as simulation_engine  # noqa: E402
from infrastructure.logging.structured_logger import configure_logging, get_logger  # noqa: E402

# Barrido manual de área de salida (m^2) — sustituido por Optuna en Phase 5.
EXIT_AREA_SWEEP = [1e-5, 1.2e-5, 1.5e-5, 2e-5, 3e-5]


def build_requirements():
    engine = RequirementsEngine()
    return engine.build(
        problem="Maximizar Isp de un thruster de gas frío (N2) variando el área de salida de la tobera",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        variables={
            "chamber_pressure": Parameter(name="chamber_pressure", value=5e5, unit="Pa", type=ParameterType.FIXED),
            "chamber_temperature": Parameter(
                name="chamber_temperature", value=300.0, unit="K", type=ParameterType.FIXED
            ),
            "throat_area": Parameter(name="throat_area", value=1e-6, unit="m^2", type=ParameterType.FIXED),
            "nozzle_exit_area": Parameter(
                name="nozzle_exit_area",
                value=EXIT_AREA_SWEEP[0],
                unit="m^2",
                type=ParameterType.FREE,
                range=(1e-6, 1e-3),
            ),
            "ambient_pressure": Parameter(name="ambient_pressure", value=0.0, unit="Pa", type=ParameterType.FIXED),
            "gas_gamma": Parameter(name="gas_gamma", value=1.4, unit=None, type=ParameterType.FIXED),
            "gas_constant": Parameter(
                name="gas_constant", value=296.8, unit="J/(kg*K)", type=ParameterType.FIXED
            ),
        },
        validation_requirements=["Benchmarks de V&V en tests/benchmarks/test_cold_gas_benchmark.py"],
    )


def make_design_step():
    """Design Agent real = Phase 6. Aquí: barrido manual determinista por iteración."""

    def design_step(state: ProjectState):
        # state.iteration ya fue incrementado por el Orchestrator antes
        # de llamar a este step (1-indexed); la primera iteración crea el
        # baseline con EXIT_AREA_SWEEP[0], las siguientes lo modifican.
        iteration_idx = min(state.iteration - 1, len(EXIT_AREA_SWEEP) - 1)
        area = EXIT_AREA_SWEEP[iteration_idx]
        if state.baseline_design is None:
            return create(domain=state.requirements.domain, parameters=dict(state.requirements.variables))
        return modify(state.baseline_design, {"nozzle_exit_area": area})

    return design_step


def simulate_step(design):
    return simulation_engine.run(design)


def make_evaluate_step():
    def evaluate_step(baseline_results, candidate_results: Results) -> EvaluationResult:
        if baseline_results is None:
            return EvaluationResult(improved=None, confidence=candidate_results.confidence)
        delta = candidate_results.predictions.get("specific_impulse", 0.0) - baseline_results.predictions.get(
            "specific_impulse", 0.0
        )
        return EvaluationResult(
            metric_deltas={"specific_impulse": delta},
            improved=delta > 0,
            confidence=min(baseline_results.confidence or 0, candidate_results.confidence or 0),
        )

    return evaluate_step


def critique_step(design, results: Results, evaluation: EvaluationResult) -> Verdict:
    """Critic Agent real (LLM) = Phase 6. Aquí: reglas explícitas sobre evidencia física real."""
    if results.model_validity == "unknown":
        return Verdict(decision="REJECT", findings=["INSUFFICIENT EVIDENCE: sin PhysicsModel aplicable."])
    findings = []
    if results.model_validity != "within_range":
        findings.append("Resultado fuera del validity_range declarado del PhysicsModel.")
    if results.predictions.get("exit_mach", 0) < 1.0:
        findings.append("Mach de salida < 1: viola el supuesto de flujo atorado.")
    decision = "REJECT" if findings else "ACCEPT"
    return Verdict(decision=decision, findings=findings)


def main() -> None:
    configure_logging()
    log = get_logger(component="phase3_vertical_slice")

    requirements = build_requirements()
    store = SQLiteExperimentStore("gede_phase3.db")
    orchestrator = Orchestrator(
        store,
        design_step=make_design_step(),
        simulate_step=simulate_step,
        evaluate_step=make_evaluate_step(),
        critique_step=critique_step,
    )
    budget = Budget(
        max_iterations=len(EXIT_AREA_SWEEP),
        max_simulations=20,
        max_llm_calls=1,  # Phase 3: sin agentes LLM todavía, pero 0 bloquearía el loop (0 >= 0)
        max_runtime_seconds=60,
        max_research_calls=1,
    )

    result = orchestrator.run(requirements, budget=budget)

    log.info(
        "run_finished",
        stopping_reason=result.stopping_reason.value,
        iterations=result.budget_tracker.iterations,
        experiments_saved=len(result.experiment_graph.nodes),
    )

    print("\n--- REPORT (Phase 3 — física real, sin agentes LLM todavía) ---")
    print(f"Problema: {requirements.problem}")
    print(f"Razón de parada: {result.stopping_reason.value}")
    print(f"Experimentos: {len(result.experiment_graph.nodes)}\n")

    print(f"{'exit_area (m^2)':>18} | {'area_ratio':>10} | {'Isp (s)':>8} | {'thrust (N)':>10} | {'verdict':>8}")
    for exp_id in result.final_state.experiment_history:
        exp = store.get(exp_id)
        area = exp.design.parameters["nozzle_exit_area"].value
        ratio = exp.results.predictions.get("area_ratio", float("nan"))
        isp = exp.results.predictions.get("specific_impulse", float("nan"))
        thrust = exp.results.predictions.get("thrust", float("nan"))
        print(f"{area:>18.2e} | {ratio:>10.2f} | {isp:>8.2f} | {thrust:>10.4f} | {exp.verdict.decision:>8}")


if __name__ == "__main__":
    main()
