"""
DoD de Phase 1 (Architecture Design Document, sección 18):
"Se puede crear un Requirements -> Design -> Experiment vacío y
guardarlo/recuperarlo".

Este test cubre ese ciclo completo con los defaults reales (sin steps
inyectados) para demostrar que, sin ningún PhysicsModel todavía, el
sistema NUNCA inventa un resultado: se detiene explícitamente por
INSUFFICIENT EVIDENCE (Principio Fundamental, sección 2).
"""
from core.experiments.schema import ExperimentStatus
from core.experiments.store import SQLiteExperimentStore
from core.orchestrator.budget import Budget, StoppingReason
from core.orchestrator.orchestrator import Orchestrator
from core.requirements.engine import RequirementsEngine
from core.requirements.schema import Objective, Parameter, ParameterType


def test_full_cycle_with_no_physics_model_yet_yields_insufficient_evidence(tmp_path):
    eng = RequirementsEngine()
    requirements = eng.build(
        problem="Maximizar Isp de un thruster de gas frío",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        variables={
            "nozzle_exit_area": Parameter(
                name="nozzle_exit_area", value=1e-5, unit="m^2", type=ParameterType.FREE, range=(1e-6, 1e-4)
            ),
            "chamber_pressure": Parameter(
                name="chamber_pressure", value=5e5, unit="Pa", type=ParameterType.FIXED
            ),
        },
    )

    store = SQLiteExperimentStore(tmp_path / "vertical_slice.db")
    orchestrator = Orchestrator(store)
    budget = Budget(max_iterations=5, max_simulations=10, max_llm_calls=10, max_runtime_seconds=60, max_research_calls=10)

    result = orchestrator.run(requirements, budget=budget)

    # El sistema debe pararse honestamente, no inventar un "diseño exitoso".
    assert result.stopping_reason == StoppingReason.INSUFFICIENT_EVIDENCE
    assert result.budget_tracker.iterations == 1

    experiment_id = result.final_state.experiment_history[0]
    experiment = store.get(experiment_id)
    assert experiment.status == ExperimentStatus.REJECTED
    assert "INSUFFICIENT EVIDENCE" in experiment.verdict.findings[0]

    # Reproducibilidad básica: el Design guardado en el Experiment es
    # recuperable y conserva los parámetros originales de Requirements.
    assert experiment.design.parameters["nozzle_exit_area"].value == 1e-5
    assert experiment.design.parameters["chamber_pressure"].unit == "Pa"

    # Trazabilidad (secc. 43, preguntas 1-2): se puede responder qué
    # diseño se evaluó y con qué requirements.
    assert experiment.requirements.problem == requirements.problem


def test_dimensional_gate_blocks_before_any_simulation(tmp_path):
    """
    El gate de Dimensional Analysis debe bloquear ANTES de crear
    cualquier experimento si las unidades son inválidas.
    """
    from core.requirements.schema import Requirements

    bad_requirements = Requirements(
        problem="unidades inválidas",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        variables={"bad": Parameter(name="bad", value=1.0, unit="not_a_real_unit", type=ParameterType.FIXED)},
    )

    store = SQLiteExperimentStore(tmp_path / "blocked.db")
    orchestrator = Orchestrator(store)
    budget = Budget(max_iterations=5, max_simulations=10, max_llm_calls=10, max_runtime_seconds=60, max_research_calls=10)

    result = orchestrator.run(bad_requirements, budget=budget)

    assert result.stopping_reason == StoppingReason.CONSTRAINT_VIOLATION
    assert result.budget_tracker.iterations == 0
    assert len(result.experiment_graph.nodes) == 0
