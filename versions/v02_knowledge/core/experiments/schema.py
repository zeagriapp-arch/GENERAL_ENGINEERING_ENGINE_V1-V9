"""
Experiment Memory schemas (secciones 21 y 22).

Un Experiment es INMUTABLE una vez CRITIQUED (ACCEPTED/REJECTED). Para
"modificarlo" se crea un experimento hijo (parent_id) — esto es lo que
permite reconstruir el Experiment Graph.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from core.design.schema import Design
from core.requirements.schema import Requirements


class ExperimentStatus(str, Enum):
    PENDING = "PENDING"
    SIMULATED = "SIMULATED"
    EVALUATED = "EVALUATED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class Results(BaseModel):
    """Salida de Simulation Engine + Uncertainty Engine (secciones 15/20)."""

    predictions: dict[str, float] = Field(default_factory=dict)
    units: dict[str, str] = Field(default_factory=dict)
    confidence: float | None = None  # None == "unknown"
    uncertainty: dict[str, float] | None = None
    model_validity: str = "unknown"  # within_range | extrapolated | out_of_range | unknown
    data_quality: str = "unknown"  # high | medium | low | unknown


class EvaluationResult(BaseModel):
    """Salida de Evaluation Engine (sección 18)."""

    metric_deltas: dict[str, float] = Field(default_factory=dict)
    constraint_violations: list[str] = Field(default_factory=list)
    improved: bool | None = None  # None == "unknown"
    confidence: float | None = None


class Verdict(BaseModel):
    """Salida de Critic Engine (sección 19)."""

    decision: str  # "ACCEPT" | "REJECT"
    findings: list[str] = Field(default_factory=list)
    dimensional_issues: list[str] = Field(default_factory=list)
    unjustified_conclusions: list[str] = Field(default_factory=list)


class Experiment(BaseModel):
    id: str = Field(default_factory=_new_id)
    parent_id: Optional[str] = None
    requirements: Requirements
    design: Design
    assumptions: list[str] = Field(default_factory=list)
    model_ref: Optional[str] = None
    solver_config: dict[str, Any] = Field(default_factory=dict)
    results: Optional[Results] = None
    metrics: Optional[EvaluationResult] = None
    verdict: Optional[Verdict] = None
    sources: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    software_version: str = "0.1.0"
    model_version: Optional[str] = None
    status: ExperimentStatus = ExperimentStatus.PENDING

    def is_closed(self) -> bool:
        return self.status in (ExperimentStatus.ACCEPTED, ExperimentStatus.REJECTED, ExperimentStatus.FAILED)


class ExperimentGraph(BaseModel):
    """Nodo raíz + hijos, para responder qué se intentó / qué produjo mejora (sección 22)."""

    root_id: str
    nodes: dict[str, Experiment]
    edges: list[tuple[str, str]]  # (parent_id, child_id)

    def children_of(self, experiment_id: str) -> list[Experiment]:
        return [self.nodes[c] for (p, c) in self.edges if p == experiment_id]
