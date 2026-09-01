from __future__ import annotations

import pytest
from pydantic import ValidationError

from design_contract.variables import DesignDomain, DesignDomainType, VariableRole
from tests.conftest import make_provenance, make_variable


class TestContinuousDomain:
    def test_valid_bounds(self):
        d = DesignDomain.continuous(0.1, 0.5)
        assert d.contains(0.3)
        assert not d.contains(0.05)
        assert not d.contains(0.6)

    def test_bounds_inclusive(self):
        d = DesignDomain.continuous(0.1, 0.5)
        assert d.contains(0.1) and d.contains(0.5)

    def test_requires_both_bounds(self):
        with pytest.raises(ValidationError):
            DesignDomain(kind=DesignDomainType.CONTINUOUS, lower_bound=0.1)

    def test_lower_must_not_exceed_upper(self):
        with pytest.raises(ValidationError):
            DesignDomain(kind=DesignDomainType.CONTINUOUS, lower_bound=0.5, upper_bound=0.1)

    def test_non_numeric_value_not_contained(self):
        d = DesignDomain.continuous(0.1, 0.5)
        assert not d.contains("A")


class TestIntegerDomain:
    def test_valid_range(self):
        d = DesignDomain.integer(1, 20)
        assert d.contains(5)
        assert not d.contains(21)

    def test_non_integer_float_not_contained(self):
        d = DesignDomain.integer(1, 20)
        assert not d.contains(5.5)

    def test_bool_not_contained_despite_being_int_subclass(self):
        d = DesignDomain.integer(0, 1)
        assert not d.contains(True)


class TestDiscreteDomain:
    def test_valid_values(self):
        d = DesignDomain.discrete([1, 3, 5, 7])
        assert d.contains(3)
        assert not d.contains(4)

    def test_requires_non_empty_allowed_values(self):
        with pytest.raises(ValidationError):
            DesignDomain(kind=DesignDomainType.DISCRETE, allowed_values=[])


class TestCategoricalDomain:
    def test_valid_category(self):
        d = DesignDomain.categorical(["A", "B", "C"])
        assert d.contains("B")
        assert not d.contains("D")

    def test_requires_non_empty_allowed_values(self):
        with pytest.raises(ValidationError):
            DesignDomain(kind=DesignDomainType.CATEGORICAL, allowed_values=None)


class TestBooleanDomain:
    def test_default_allowed_values_autofilled(self):
        d = DesignDomain.boolean()
        assert d.contains(True) and d.contains(False)
        assert not d.contains("true")

    def test_explicit_construction_autofills_too(self):
        d = DesignDomain(kind=DesignDomainType.BOOLEAN)
        assert d.allowed_values == [True, False]


class TestVariableRoles:
    @pytest.mark.parametrize("role", [VariableRole.DESIGN, VariableRole.FIXED, VariableRole.DERIVED, VariableRole.CONTROL])
    def test_each_role_constructs(self, role):
        var = make_variable("x", role=role)
        assert var.role == role

    def test_type_property_mirrors_domain_kind(self):
        var = make_variable("diameter", domain=DesignDomain.continuous(0.1, 0.5))
        assert var.type == DesignDomainType.CONTINUOUS

    def test_contains_delegates_to_domain(self):
        var = make_variable("material", domain=DesignDomain.categorical(["A", "B"]), unit=None)
        assert var.contains("A")
        assert not var.contains("Z")

    def test_variable_requires_provenance(self):
        with pytest.raises(ValidationError):
            from design_contract.variables import DesignVariable

            DesignVariable(name="x", domain=DesignDomain.continuous(0, 1))
