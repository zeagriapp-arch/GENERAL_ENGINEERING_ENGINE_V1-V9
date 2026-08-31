import pytest

from core.design.repository import create
from core.experiments.schema import Experiment, ExperimentGraph, ExperimentStatus, Results, Verdict
from core.orchestrator.report import generate_report
from core.requirements.schema import Constraint, Objective, Parameter, ParameterType, Requirements
from core.simulation import engine as simulation_engine
from domains.satellite.propulsion.simulation_adapters.cold_gas_solver import ColdGasNozzleSolver


@pytest.fixture(autouse=True)
def _register_solver():
    simulation_engine.unregister_all()
    simulation_engine.register_solver("satellite.propulsion", ColdGasNozzleSolver())
    yield
    simulation_engine.unregister_all()


def _requirements():
    return Requirements(
        problem="test report",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
        constraints=[Constraint(name="min_thrust", expression="thrust >= 0.5", hard=True)],
    )


def _design():
    values = {
        "chamber_pressure": 5e5, "chamber_temperature": 300.0, "throat_area": 1e-6,
        "nozzle_exit_area": 2e-5, "ambient_pressure": 0.0, "gas_gamma": 1.4, "gas_constant": 296.8,
    }
    params = {}
    for name, v in values.items():
        ptype = ParameterType.FREE if name == "nozzle_exit_area" else ParameterType.FIXED
        params[name] = Parameter(name=name, value=v, type=ptype)
    return create(domain="satellite.propulsion", parameters=params, provenance=["source:test-doc"])


def test_report_answers_all_12_questions_with_real_physics():
    design = _design()
    solver = ColdGasNozzleSolver()
    results = solver.run(design)
    requirements = _requirements()
    experiment = Experiment(
        requirements=requirements, design=design, results=results,
        verdict=Verdict(decision="ACCEPT", findings=[]), status=ExperimentStatus.ACCEPTED,
    )
    graph = ExperimentGraph(root_id=experiment.id, nodes={experiment.id: experiment}, edges=[])

    report = generate_report(experiment, graph)

    assert report.design_summary["nozzle_exit_area"] == 2e-5
    assert report.changed_variables == {"nozzle_exit_area": 2e-5}
    assert report.model_used == "cold_gas_thruster_ideal_nozzle"
    assert len(report.assumptions) > 0
    assert "thrust" in report.results
    assert report.confidence == pytest.approx(0.9)
    assert report.constraints_status["min_thrust"] == "SATISFIED"
    assert report.sources == ["source:test-doc"]
    assert report.prior_experiments == []  # es la raíz
    assert report.reproducible is True


def test_report_marks_violated_constraint():
    design = _design()
    results = Results(predictions={"thrust": 0.1}, model_validity="within_range", confidence=0.9)
    requirements = _requirements()
    experiment = Experiment(
        requirements=requirements, design=design, results=results,
        verdict=Verdict(decision="REJECT", findings=["constraint violado"]), status=ExperimentStatus.REJECTED,
    )
    graph = ExperimentGraph(root_id=experiment.id, nodes={experiment.id: experiment}, edges=[])

    report = generate_report(experiment, graph)
    assert report.constraints_status["min_thrust"] == "VIOLATED"


def test_report_traces_prior_experiments_via_parent_chain():
    root_design = _design()
    root = Experiment(requirements=_requirements(), design=root_design, status=ExperimentStatus.ACCEPTED)

    child_design = root_design.model_copy(update={"id": "child-1", "parent_id": root.id})
    child = Experiment(
        parent_id=root.id, requirements=_requirements(), design=child_design,
        results=Results(predictions={"thrust": 0.9}, model_validity="within_range", confidence=0.9),
        status=ExperimentStatus.ACCEPTED,
    )

    graph = ExperimentGraph(root_id=root.id, nodes={root.id: root, child.id: child}, edges=[(root.id, child.id)])
    report = generate_report(child, graph)

    assert report.prior_experiments == [root.id]


def test_report_without_registered_solver_marks_not_reproducible():
    simulation_engine.unregister_all()  # override del fixture
    design = _design()
    results = Results(predictions={"thrust": 0.9}, model_validity="within_range", confidence=0.9)
    experiment = Experiment(requirements=_requirements(), design=design, results=results, status=ExperimentStatus.ACCEPTED)
    graph = ExperimentGraph(root_id=experiment.id, nodes={experiment.id: experiment}, edges=[])

    report = generate_report(experiment, graph)

    assert report.model_used == "unknown"
    assert report.reproducible is False


def test_report_without_results_is_honest_not_fabricated():
    design = _design()
    experiment = Experiment(requirements=_requirements(), design=design, results=None, status=ExperimentStatus.PENDING)
    graph = ExperimentGraph(root_id=experiment.id, nodes={experiment.id: experiment}, edges=[])

    report = generate_report(experiment, graph)

    assert report.results == {}
    assert "No se ejecutó ninguna simulación" in report.simulation_summary
    assert report.constraints_status["min_thrust"] == "UNKNOWN"


def test_summary_text_includes_all_12_numbered_sections():
    design = _design()
    solver = ColdGasNozzleSolver()
    results = solver.run(design)
    experiment = Experiment(requirements=_requirements(), design=design, results=results, status=ExperimentStatus.ACCEPTED)
    graph = ExperimentGraph(root_id=experiment.id, nodes={experiment.id: experiment}, edges=[])

    text = generate_report(experiment, graph).summary_text()
    for marker in ["1-3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", "11.", "12."]:
        assert marker in text
