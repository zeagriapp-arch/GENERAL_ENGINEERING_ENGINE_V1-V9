import pytest

from core.experiments.schema import Results
from core.requirements.schema import ParameterType
from domains.satellite.propulsion.evaluation_metrics import compare_to_baseline, isp_efficiency
from domains.satellite.propulsion.requirements_schema import DOMAIN, build_cold_gas_requirements


def test_build_cold_gas_requirements_has_all_required_variables():
    req = build_cold_gas_requirements("test problem")
    required = {
        "chamber_pressure", "chamber_temperature", "throat_area", "nozzle_exit_area",
        "ambient_pressure", "gas_gamma", "gas_constant",
    }
    assert required.issubset(set(req.variables))
    assert req.domain == DOMAIN


def test_build_cold_gas_requirements_exit_area_is_free_with_range():
    req = build_cold_gas_requirements("test")
    var = req.variables["nozzle_exit_area"]
    assert var.type == ParameterType.FREE
    assert var.range is not None


def test_build_cold_gas_requirements_min_thrust_creates_hard_constraint():
    req = build_cold_gas_requirements("test", min_thrust=0.8)
    assert len(req.constraints) == 1
    assert req.constraints[0].hard
    assert "0.8" in req.constraints[0].expression


def test_build_cold_gas_requirements_no_min_thrust_means_no_constraints():
    req = build_cold_gas_requirements("test")
    assert req.constraints == []


def test_fixed_overrides_change_defaults():
    req = build_cold_gas_requirements("test", fixed_overrides={"chamber_pressure": 1e6})
    assert req.variables["chamber_pressure"].value == 1e6


def test_isp_efficiency_computes_fraction():
    results = Results(predictions={"specific_impulse": 70.0})
    efficiency = isp_efficiency(results, theoretical_max_isp=100.0)
    assert efficiency == 0.7


def test_isp_efficiency_returns_none_when_missing_data():
    results = Results(predictions={})
    assert isp_efficiency(results, theoretical_max_isp=100.0) is None


def test_compare_to_baseline_computes_relative_deltas():
    baseline = Results(predictions={"thrust": 1.0, "isp": 70.0})
    candidate = Results(predictions={"thrust": 1.1, "isp": 73.5})
    deltas = compare_to_baseline(baseline, candidate)
    assert deltas["thrust"] == pytest.approx(0.1)
    assert round(deltas["isp"], 2) == 0.05


def test_compare_to_baseline_skips_missing_or_zero_baseline_keys():
    baseline = Results(predictions={"thrust": 0.0, "shared": 5.0})
    candidate = Results(predictions={"thrust": 1.0, "shared": 6.0, "new_key": 9.0})
    deltas = compare_to_baseline(baseline, candidate)
    assert "thrust" not in deltas  # baseline era 0 -> división indefinida, se omite
    assert "new_key" not in deltas  # no existía en baseline
    assert deltas["shared"] == pytest.approx(0.2)
