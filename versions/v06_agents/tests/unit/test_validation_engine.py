from core.numerical.interfaces import ConvergenceStatus
from core.physics.schema import ConstraintKind, PhysicsConstraint
from core.simulation.schema import ResultState, SimulationResult
from core.validation.engine import ValidationEngine
from core.validation.schema import BenchmarkRunResult


def _success_sim(outputs=None):
    return SimulationResult(
        simulation_id="s1",
        status=ResultState.SUCCESS,
        outputs=outputs or {"mach": 2.0},
        convergence=ConvergenceStatus.CONVERGED,
    )


def test_all_checks_pass_gives_overall_valid():
    engine = ValidationEngine()
    report = engine.validate(_success_sim())
    assert report.input_validity
    assert report.dimensional_consistency
    assert report.model_validity
    assert report.numerical_convergence
    assert report.overall_valid


def test_input_errors_fail_overall():
    engine = ValidationEngine()
    report = engine.validate(_success_sim(), input_errors=["falta parámetro X"])
    assert not report.input_validity
    assert not report.overall_valid


def test_non_converged_fails_numerical_convergence():
    engine = ValidationEngine()
    sim = SimulationResult(simulation_id="s2", status=ResultState.NON_CONVERGED, convergence=ConvergenceStatus.NOT_CONVERGED)
    report = engine.validate(sim)
    assert not report.numerical_convergence
    assert not report.overall_valid


def test_constraints_violated_marks_physical_constraints():
    engine = ValidationEngine()
    constraint = PhysicsConstraint(name="mach_supersonic", kind=ConstraintKind.PHYSICAL, expression="mach >= 1.0")
    report = engine.validate(_success_sim(outputs={"mach": 0.5}), constraints=[constraint])
    assert report.physical_constraints == "VIOLATED"
    assert not report.overall_valid


def test_constraints_unknown_does_not_mean_satisfied():
    engine = ValidationEngine()
    constraint = PhysicsConstraint(name="needs_missing_var", kind=ConstraintKind.PHYSICAL, expression="p_ratio >= 1.0")
    report = engine.validate(_success_sim(outputs={"mach": 2.0}), constraints=[constraint])
    assert report.physical_constraints == "UNKNOWN"
    assert not report.overall_valid  # UNKNOWN no cuenta como válido


def test_benchmark_comparison_failed_fails_overall():
    engine = ValidationEngine()
    bad_benchmark = BenchmarkRunResult(benchmark_id="b1", passed=False, max_relative_error=0.5, detail="too far off")
    report = engine.validate(_success_sim(), benchmark_result=bad_benchmark)
    assert report.benchmark_comparison == "FAILED"
    assert not report.overall_valid
