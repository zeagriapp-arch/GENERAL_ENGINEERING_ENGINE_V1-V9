from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_contract.schema import Uncertainty, UncertaintyType


class TestUncertaintyNone:
    def test_default_is_none(self):
        u = Uncertainty()
        assert u.type == UncertaintyType.NONE


class TestUncertaintyUnknown:
    def test_unknown_needs_no_extra_fields(self):
        u = Uncertainty(type=UncertaintyType.UNKNOWN)
        assert u.type == UncertaintyType.UNKNOWN


class TestUncertaintyInterval:
    def test_valid_interval(self):
        u = Uncertainty(type=UncertaintyType.INTERVAL, lower=295.0, upper=305.0, unit="K")
        assert u.lower == 295.0 and u.upper == 305.0

    def test_interval_requires_lower_and_upper(self):
        with pytest.raises(ValidationError):
            Uncertainty(type=UncertaintyType.INTERVAL, lower=295.0)

    def test_interval_lower_must_not_exceed_upper(self):
        with pytest.raises(ValidationError):
            Uncertainty(type=UncertaintyType.INTERVAL, lower=310.0, upper=305.0)


class TestUncertaintyPercentage:
    def test_valid_percentage(self):
        u = Uncertainty(type=UncertaintyType.PERCENTAGE, percentage=5.0)
        assert u.percentage == 5.0

    def test_percentage_requires_value(self):
        with pytest.raises(ValidationError):
            Uncertainty(type=UncertaintyType.PERCENTAGE)


class TestUncertaintyDistribution:
    def test_valid_distribution(self):
        u = Uncertainty(type=UncertaintyType.DISTRIBUTION, distribution_name="normal", distribution_params={"mean": 300.0, "std": 5.0})
        assert u.distribution_name == "normal"
        assert u.distribution_params["std"] == 5.0

    def test_distribution_requires_name(self):
        with pytest.raises(ValidationError):
            Uncertainty(type=UncertaintyType.DISTRIBUTION, distribution_params={"mean": 300.0})
