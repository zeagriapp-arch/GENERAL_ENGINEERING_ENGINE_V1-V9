from core.physics.schema import (
    Assumption,
    ConstraintKind,
    ConstraintStatus,
    Parameter,
    PhysicsConstraint,
    RiskLevel,
    Variable,
    VariableType,
)


def test_variable_creation():
    v = Variable(name="thrust", symbol="F", value=1.0, unit="N", type=VariableType.OUTPUT, domain="mechanics")
    assert v.type == VariableType.OUTPUT
    assert v.status == "unset"


def test_parameter_with_bounds_and_confidence():
    p = Parameter(name="gamma", value=1.4, lower_bound=1.0, upper_bound=1.8, confidence=0.95, mutable=False)
    assert p.lower_bound == 1.0
    assert not p.mutable


def test_assumption_has_risk_level_default():
    a = Assumption(description="Flujo isentrópico", affected_model="cold_gas_thruster")
    assert a.risk_level == RiskLevel.MEDIUM


class TestConstraintEvaluation:
    def test_satisfied(self):
        c = PhysicsConstraint(name="mach_supersonic", kind=ConstraintKind.PHYSICAL, expression="mach >= 1.0")
        assert c.evaluate({"mach": 2.0}) == ConstraintStatus.SATISFIED

    def test_violated(self):
        c = PhysicsConstraint(name="mach_supersonic", kind=ConstraintKind.PHYSICAL, expression="mach >= 1.0")
        assert c.evaluate({"mach": 0.5}) == ConstraintStatus.VIOLATED

    def test_unknown_when_variable_missing(self):
        """Nunca asumir que falta de datos == satisfecho (sección 9)."""
        c = PhysicsConstraint(name="mach_supersonic", kind=ConstraintKind.PHYSICAL, expression="mach >= 1.0")
        assert c.evaluate({}) == ConstraintStatus.UNKNOWN

    def test_unknown_on_malformed_expression(self):
        c = PhysicsConstraint(name="weird", kind=ConstraintKind.PHYSICAL, expression="not a valid expr!!")
        assert c.evaluate({"x": 1.0}) == ConstraintStatus.UNKNOWN

    def test_equality_within_tolerance(self):
        c = PhysicsConstraint(name="eq", kind=ConstraintKind.EQUALITY, expression="x == 1.0")
        assert c.evaluate({"x": 1.0 + 1e-12}) == ConstraintStatus.SATISFIED
