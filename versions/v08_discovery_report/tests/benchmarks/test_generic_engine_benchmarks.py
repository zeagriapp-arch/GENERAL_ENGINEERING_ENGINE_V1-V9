"""
Vertical slice de la Phase 3 ampliada (sección 44):

KNOWN PHYSICAL PROBLEM -> PhysicsModel -> Parameter/Unit validation ->
Numerical Solver -> SimulationResult -> Analytical/Benchmark Validation
-> ValidationReport -> (Experiment Storage ya probado en Phase 1).

Cubre los dos benchmarks genéricos (algebraico + ODE), con
ValidationEngine end-to-end y regression testing.
"""
import pytest

from core.numerical.interfaces import ConvergenceStatus
from core.physics.benchmark_models.constant_acceleration import ConstantAccelerationModel
from core.physics.benchmark_models.mass_spring_oscillator import MassSpringOscillatorModel, analytical_solution
from core.physics.equation_system import EquationSpec, EquationSystem
from core.physics.interfaces import PhysicsInputs
from core.simulation.schema import ResultState, SimulationResult
from core.validation.benchmark_runner import run_benchmark
from core.validation.engine import ValidationEngine
from core.validation.regression_store import RegressionStore
from core.validation.schema import BenchmarkCase


@pytest.fixture
def regression_store(tmp_path):
    return RegressionStore(tmp_path / "regressions.json")


def test_constant_acceleration_full_pipeline(regression_store):
    model = ConstantAccelerationModel()

    # 1. Parameter/unit validation (EquationSystem, sección 6/7)
    eq_system = EquationSystem(
        [
            EquationSpec(
                equation_id="kinematics-position",
                expression="x = x0 + v0*t + 0.5*a*t^2",
                variables={"x": "posición", "x0": "posición inicial", "v0": "velocidad inicial", "a": "aceleración", "t": "tiempo"},
                units={"x": "m", "x0": "m", "v0": "m/s", "a": "m/s^2", "t": "s"},
            )
        ]
    )
    eq_errors = eq_system.validate(
        available_variables={"x", "x0", "v0", "a", "t"}, available_parameters=set()
    )
    assert eq_errors == []

    # 2. Numerical solver (aquí: cálculo directo, ya que es algebraico)
    case = model.validation_cases[0]
    outputs = model.compute(PhysicsInputs(values=case["known_inputs"]))

    # 3. SimulationResult
    sim_result = SimulationResult(
        simulation_id="bench-const-accel",
        status=ResultState.SUCCESS if outputs.within_validity_range else ResultState.OUT_OF_RANGE,
        outputs=outputs.values,
        convergence=ConvergenceStatus.CONVERGED,  # cerrado, no iterativo
    )

    # 4. Benchmark comparison contra expected_outputs conocidos
    benchmark_case = BenchmarkCase(
        benchmark_id="const-accel-freefall-2s",
        description="Caída libre 2s desde reposo, a=9.8 m/s^2",
        known_inputs=case["known_inputs"],
        expected_outputs=case["expected_outputs"],
        tolerance=1e-6,
        model_id=model.model_id,
    )
    benchmark_result = run_benchmark(benchmark_case, model)
    assert benchmark_result.passed, benchmark_result.detail

    # 5. ValidationReport
    validator = ValidationEngine()
    report = validator.validate(sim_result, benchmark_result=benchmark_result)
    assert report.overall_valid

    # 6. Regression testing (sección 27)
    regression = regression_store.check(benchmark_case.benchmark_id, outputs.values)
    assert regression.is_first_run
    regression_store.record(benchmark_case.benchmark_id, outputs.values)
    regression_again = regression_store.check(benchmark_case.benchmark_id, outputs.values)
    assert not regression_again.regression_detected


def test_mass_spring_oscillator_full_pipeline(regression_store):
    model = MassSpringOscillatorModel()
    mass, k, x0, v0, t = 1.0, 4.0, 1.0, 0.0, 1.0
    inputs = {"mass": mass, "spring_constant": k, "initial_position": x0, "initial_velocity": v0, "time": t}

    outputs = model.compute(PhysicsInputs(values=inputs))
    x_analytical, v_analytical = analytical_solution(mass, k, x0, v0, t)

    sim_result = SimulationResult(
        simulation_id="bench-mass-spring",
        status=ResultState.SUCCESS,
        outputs=outputs.values,
        convergence=ConvergenceStatus.CONVERGED,
    )

    benchmark_case = BenchmarkCase(
        benchmark_id="mass-spring-1s",
        description="Oscilador m=1kg, k=4N/m, x0=1m, en reposo, evaluado en t=1s",
        known_inputs=inputs,
        expected_outputs={"position": x_analytical, "velocity": v_analytical},
        tolerance=1e-5,
        model_id=model.model_id,
    )
    benchmark_result = run_benchmark(benchmark_case, model)
    assert benchmark_result.passed, benchmark_result.detail

    validator = ValidationEngine()
    report = validator.validate(sim_result, benchmark_result=benchmark_result)
    assert report.overall_valid
    assert report.numerical_convergence  # el ODE solver sí convergió

    regression = regression_store.check(benchmark_case.benchmark_id, outputs.values)
    assert regression.is_first_run
    regression_store.record(benchmark_case.benchmark_id, outputs.values)


def test_out_of_range_input_fails_validation_explicitly():
    """Sección 10: fuera de validity_range -> marcado explícito, nunca silencioso."""
    model = MassSpringOscillatorModel()
    huge_time = 1e5  # fuera de validity_range["time"] = (0, 1e4)
    outputs = model.compute(
        PhysicsInputs(values={"mass": 1.0, "spring_constant": 4.0, "initial_position": 1.0, "initial_velocity": 0.0, "time": huge_time})
    )
    assert not outputs.within_validity_range
    assert any("time" in note for note in outputs.validity_notes)

    sim_result = SimulationResult(
        simulation_id="out-of-range-test",
        status=ResultState.OUT_OF_RANGE,
        outputs=outputs.values,
        convergence=ConvergenceStatus.CONVERGED,
    )
    report = ValidationEngine().validate(sim_result)
    assert not report.model_validity
    assert not report.overall_valid
