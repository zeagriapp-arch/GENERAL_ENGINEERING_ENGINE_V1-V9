from core.design.candidate import build_design, check_design_space_constraints, evaluate_requirements
from core.design.design_space import DesignSpace, DesignVariable
from core.experiments.schema import Results
from core.requirements.schema import Constraint, Objective, Parameter, ParameterType, Requirements


def _requirements(**constraints_kwargs):
    return Requirements(
        problem="test",
        domain="generic.mechanics",
        objectives=[Objective(name="obj", direction="maximize", metric="metric_a")],
        constraints=[Constraint(name="c1", expression="metric_a >= 10.0", hard=True)],
        variables={"free_x": Parameter(name="free_x", value=1.0, type=ParameterType.FREE, range=(0.0, 10.0))},
    )


def test_build_design_includes_fixed_and_free_params():
    req = _requirements()
    space = DesignSpace.from_requirements(req)
    design = build_design(req, space, {"free_x": 5.0})
    assert design.parameters["free_x"].value == 5.0
    assert design.domain == "generic.mechanics"


def test_check_design_space_constraints_detects_violation():
    space = DesignSpace(
        domain="d",
        variables={"x": DesignVariable(name="x", lower_bound=0.0, upper_bound=10.0, constraint="x <= 5.0")},
    )
    violations = check_design_space_constraints(space, {"x": 8.0})
    assert len(violations) == 1


def test_check_design_space_constraints_passes_when_satisfied():
    space = DesignSpace(
        domain="d",
        variables={"x": DesignVariable(name="x", lower_bound=0.0, upper_bound=10.0, constraint="x <= 5.0")},
    )
    violations = check_design_space_constraints(space, {"x": 3.0})
    assert violations == []


def test_evaluate_requirements_passes_when_valid_and_constraint_satisfied():
    req = _requirements()
    results = Results(predictions={"metric_a": 15.0}, model_validity="within_range")
    passed, reasons = evaluate_requirements(req, results)
    assert passed
    assert reasons == []


def test_evaluate_requirements_fails_on_out_of_range_model():
    req = _requirements()
    results = Results(predictions={"metric_a": 15.0}, model_validity="out_of_range")
    passed, reasons = evaluate_requirements(req, results)
    assert not passed
    assert len(reasons) == 1


def test_evaluate_requirements_fails_on_hard_constraint_violation():
    req = _requirements()
    results = Results(predictions={"metric_a": 5.0}, model_validity="within_range")
    passed, reasons = evaluate_requirements(req, results)
    assert not passed
