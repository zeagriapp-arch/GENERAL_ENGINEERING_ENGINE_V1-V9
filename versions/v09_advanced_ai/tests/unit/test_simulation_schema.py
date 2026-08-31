from core.numerical.interfaces import ConvergenceStatus
from core.simulation.schema import ResultState, SimulationResult, to_experiment_results


def test_success_converts_to_within_range_high_confidence():
    sim = SimulationResult(
        simulation_id="s1",
        status=ResultState.SUCCESS,
        outputs={"thrust": 1.0},
        convergence=ConvergenceStatus.CONVERGED,
    )
    results = to_experiment_results(sim, units={"thrust": "N"})
    assert results.model_validity == "within_range"
    assert results.confidence == 0.9
    assert results.predictions == {"thrust": 1.0}


def test_success_with_warnings_gives_medium_confidence():
    sim = SimulationResult(simulation_id="s2", status=ResultState.SUCCESS_WITH_WARNINGS)
    results = to_experiment_results(sim)
    assert results.confidence == 0.6


def test_non_converged_maps_to_unknown_validity_and_no_confidence():
    sim = SimulationResult(simulation_id="s3", status=ResultState.NON_CONVERGED)
    results = to_experiment_results(sim)
    assert results.model_validity == "unknown"
    assert results.confidence is None


def test_out_of_range_maps_correctly():
    sim = SimulationResult(simulation_id="s4", status=ResultState.OUT_OF_RANGE)
    results = to_experiment_results(sim)
    assert results.model_validity == "out_of_range"
