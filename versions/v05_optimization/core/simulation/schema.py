"""
SimulationDefinition / SimulationResult (secciones 19-22).

IMPORTANTE (compatibilidad, sección 49): el Orchestrator y ExperimentStore
de Phase 1 ya usan `core.experiments.schema.Results` — un schema más
simple. NO se reemplaza: `SimulationResult` es el schema RICO que usa
internamente el pipeline de ejecución de Phase 3 (con estados,
convergencia, runtime, etc.); `to_experiment_results()` lo colapsa al
`Results` simple para que Orchestrator siga funcionando sin cambios.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from core.experiments.schema import Results
from core.numerical.interfaces import ConvergenceStatus


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class ResultState(str, Enum):
    SUCCESS = "SUCCESS"
    SUCCESS_WITH_WARNINGS = "SUCCESS_WITH_WARNINGS"
    FAILED = "FAILED"
    INVALID_INPUT = "INVALID_INPUT"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    NON_CONVERGED = "NON_CONVERGED"
    NUMERICALLY_UNSTABLE = "NUMERICALLY_UNSTABLE"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    UNKNOWN = "UNKNOWN"


class SimulationDefinition(BaseModel):
    """Sección 19. Serializable — puede guardarse, reproducirse, versionarse."""

    simulation_id: str = Field(default_factory=_new_id)
    model_id: str
    inputs: dict[str, float] = Field(default_factory=dict)
    parameters: dict[str, float] = Field(default_factory=dict)
    initial_conditions: dict[str, float] = Field(default_factory=dict)
    boundary_conditions: dict[str, float] = Field(default_factory=dict)
    solver_id: Optional[str] = None
    solver_config: dict[str, Any] = Field(default_factory=dict)
    objectives: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    """Sección 21. Reproducible: mismo input+config -> mismo resultado."""

    simulation_id: str
    status: ResultState
    outputs: dict[str, float] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    solver_info: dict[str, Any] = Field(default_factory=dict)
    convergence: ConvergenceStatus = ConvergenceStatus.UNKNOWN
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validation_status: str = "not_validated"  # se llena vía ValidationEngine
    runtime_seconds: Optional[float] = None
    environment: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_STATUS_TO_MODEL_VALIDITY = {
    ResultState.SUCCESS: "within_range",
    ResultState.SUCCESS_WITH_WARNINGS: "within_range",
    ResultState.OUT_OF_RANGE: "out_of_range",
    ResultState.NON_CONVERGED: "unknown",
    ResultState.NUMERICALLY_UNSTABLE: "unknown",
    ResultState.VALIDATION_FAILED: "out_of_range",
    ResultState.INVALID_INPUT: "unknown",
    ResultState.FAILED: "unknown",
    ResultState.UNKNOWN: "unknown",
}

_STATUS_TO_DATA_QUALITY = {
    ResultState.SUCCESS: "high",
    ResultState.SUCCESS_WITH_WARNINGS: "medium",
}


def to_experiment_results(sim_result: SimulationResult, *, units: dict[str, str] | None = None) -> Results:
    """
    Colapsa un `SimulationResult` rico al `Results` simple que espera
    Orchestrator/ExperimentStore (Phase 1) — sin tocar esos módulos.
    """
    confidence = None
    if sim_result.status in (ResultState.SUCCESS, ResultState.SUCCESS_WITH_WARNINGS):
        confidence = 0.9 if sim_result.status == ResultState.SUCCESS else 0.6

    return Results(
        predictions=sim_result.outputs,
        units=units or {},
        confidence=confidence,
        uncertainty=None,
        model_validity=_STATUS_TO_MODEL_VALIDITY.get(sim_result.status, "unknown"),
        data_quality=_STATUS_TO_DATA_QUALITY.get(sim_result.status, "unknown"),
    )
