import pytest

from core.design.repository import create
from core.experiments.schema import Experiment, ExperimentStatus, Verdict
from core.experiments.store import ExperimentAlreadyClosedError, ExperimentNotFoundError, SQLiteExperimentStore
from core.requirements.schema import Objective, Parameter, ParameterType, Requirements


@pytest.fixture
def store(tmp_path):
    return SQLiteExperimentStore(tmp_path / "test.db")


def _requirements():
    return Requirements(
        problem="test",
        domain="satellite.propulsion",
        objectives=[Objective(name="isp", direction="maximize", metric="specific_impulse")],
    )


def _design(**params):
    return create(domain="satellite.propulsion", parameters=params)


def test_save_and_get_roundtrip(store):
    design = _design(area=Parameter(name="area", value=1e-5, unit="m^2", type=ParameterType.FREE))
    exp = Experiment(requirements=_requirements(), design=design, status=ExperimentStatus.PENDING)
    store.save(exp)
    fetched = store.get(exp.id)
    assert fetched.id == exp.id
    assert fetched.design.parameters["area"].value == 1e-5


def test_get_missing_raises():
    from core.experiments.store import SQLiteExperimentStore
    import tempfile

    s = SQLiteExperimentStore(tempfile.mktemp(suffix=".db"))
    with pytest.raises(ExperimentNotFoundError):
        s.get("does_not_exist")


def test_closed_experiment_cannot_be_resaved(store):
    design = _design()
    exp = Experiment(
        requirements=_requirements(),
        design=design,
        status=ExperimentStatus.ACCEPTED,
        verdict=Verdict(decision="ACCEPT"),
    )
    store.save(exp)
    with pytest.raises(ExperimentAlreadyClosedError):
        store.save(exp)


def test_experiment_graph_reconstructs_parent_child(store):
    root_design = _design()
    root = Experiment(requirements=_requirements(), design=root_design, status=ExperimentStatus.PENDING)
    store.save(root)

    child_design = root_design.model_copy(update={"id": "child1", "parent_id": root.id})
    child = Experiment(
        parent_id=root.id, requirements=_requirements(), design=child_design, status=ExperimentStatus.PENDING
    )
    store.save(child)

    graph = store.get_graph(root.id)
    assert root.id in graph.nodes
    assert child.id in graph.nodes
    assert (root.id, child.id) in graph.edges
    assert len(graph.children_of(root.id)) == 1


def test_find_similar_dedup(store):
    d1 = _design(area=Parameter(name="area", value=1e-5, unit="m^2", type=ParameterType.FREE))
    e1 = Experiment(requirements=_requirements(), design=d1, status=ExperimentStatus.PENDING)
    store.save(e1)

    matches = store.find_similar({"area": 1.0001e-5}, tolerance=0.01)
    assert len(matches) == 1

    no_matches = store.find_similar({"area": 5e-5}, tolerance=0.01)
    assert len(no_matches) == 0
