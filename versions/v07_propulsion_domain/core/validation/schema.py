from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationReport(BaseModel):
    """Sección 24: salida de ValidationEngine."""

    input_validity: bool
    dimensional_consistency: bool
    model_validity: bool
    numerical_convergence: bool
    physical_constraints: str  # "SATISFIED" | "VIOLATED" | "UNKNOWN" | "not_applicable"
    benchmark_comparison: Optional[str] = None  # "PASSED" | "FAILED" | None (sin benchmark)
    notes: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def overall_valid(self) -> bool:
        checks = [
            self.input_validity,
            self.dimensional_consistency,
            self.model_validity,
            self.numerical_convergence,
            self.physical_constraints in ("SATISFIED", "not_applicable"),
        ]
        if self.benchmark_comparison is not None:
            checks.append(self.benchmark_comparison == "PASSED")
        return all(checks)


class BenchmarkCase(BaseModel):
    """Sección 26."""

    benchmark_id: str
    description: str
    known_inputs: dict[str, float]
    expected_outputs: dict[str, float]
    tolerance: float = 1e-6
    reference: Optional[str] = None
    model_id: str
    solver_requirements: list[str] = Field(default_factory=list)


class BenchmarkRunResult(BaseModel):
    benchmark_id: str
    passed: bool
    max_relative_error: float
    per_output_error: dict[str, float] = Field(default_factory=dict)
    detail: str = ""
