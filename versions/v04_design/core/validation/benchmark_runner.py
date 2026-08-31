"""
Ejecuta un BenchmarkCase contra un PhysicsModel concreto (sección 26):
compara outputs calculados vs `expected_outputs` conocidos dentro de
`tolerance`.
"""
from __future__ import annotations

from core.physics.interfaces import PhysicsInputs, PhysicsModel
from core.validation.schema import BenchmarkCase, BenchmarkRunResult


def run_benchmark(case: BenchmarkCase, model: PhysicsModel) -> BenchmarkRunResult:
    outputs = model.compute(PhysicsInputs(values=case.known_inputs))

    per_output_error: dict[str, float] = {}
    for name, expected in case.expected_outputs.items():
        actual = outputs.values.get(name)
        if actual is None:
            per_output_error[name] = float("inf")
            continue
        denom = abs(expected) if expected != 0 else 1.0
        per_output_error[name] = abs(actual - expected) / denom

    max_error = max(per_output_error.values()) if per_output_error else 0.0
    passed = max_error <= case.tolerance

    return BenchmarkRunResult(
        benchmark_id=case.benchmark_id,
        passed=passed,
        max_relative_error=max_error,
        per_output_error=per_output_error,
        detail=f"max_relative_error={max_error:.3e} (tolerance={case.tolerance:.1e})",
    )
