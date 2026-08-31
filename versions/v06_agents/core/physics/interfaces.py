"""
Physics Engine — interfaces (sección 13).

NO hay un "modelo universal": cada PhysicsModel concreto vive en un
Domain Pack (`domains/*/physics_models/`) e implementa esta interfaz.
CORE solo conoce el contrato: inputs, outputs, assumptions,
validity_range, units — nunca la física en sí.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from core.design.schema import Design


class PhysicsInputs(BaseModel):
    """Valores de entrada en unidades SI (ya convertidos/validados)."""

    values: dict[str, float]


class PhysicsOutputs(BaseModel):
    """
    Salida cruda de un PhysicsModel — NO es todavía `Results` (eso lo
    construye el SimulationSolver, añadiendo confidence/model_validity
    vía Uncertainty Engine). `within_validity_range=False` es la señal
    explícita de que el modelo se evaluó fuera de su dominio declarado.
    """

    values: dict[str, float]
    units: dict[str, str]
    within_validity_range: bool
    validity_notes: list[str] = Field(default_factory=list)


class PhysicsModel(ABC):
    name: str
    validity_range: dict[str, tuple[float, float]]
    required_units: dict[str, str]

    # Metadata ampliada (Phase 3 extendida, sección 3). Todos con default
    # para no romper PhysicsModel existentes (sección 49 — compatibilidad).
    model_id: str = ""
    description: str = ""
    version: str = "0.1.0"
    uncertainty: dict[str, float] = {}
    validation_cases: list[dict] = []

    @abstractmethod
    def applies_to(self, design: Design) -> bool:
        """¿Este modelo es aplicable a este Design? (dominio + parámetros presentes)."""
        ...

    @abstractmethod
    def compute(self, inputs: PhysicsInputs) -> PhysicsOutputs: ...

    @abstractmethod
    def assumptions(self) -> list[str]: ...

    def check_validity(self, values: dict[str, float]) -> tuple[bool, list[str]]:
        """Verifica cada valor de entrada contra `validity_range`. Reutilizable por subclases."""
        notes: list[str] = []
        for name, (lo, hi) in self.validity_range.items():
            if name in values and not (lo <= values[name] <= hi):
                notes.append(f"'{name}'={values[name]} fuera de validity_range [{lo}, {hi}]")
        return (len(notes) == 0, notes)
