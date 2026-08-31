"""
SensitivityAnalyzer (sección 30): interfaz preparada, sin implementación
en V1 (decisión explícita del usuario). Phase 9 (Scientific ML /
Uncertainty Engine avanzado) implementará local sensitivity, finite
differences, y parameter sweeps sobre esta misma interfaz.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.physics.interfaces import PhysicsModel


class SensitivityAnalyzer(ABC):
    @abstractmethod
    def analyze(
        self,
        model: PhysicsModel,
        base_inputs: dict[str, float],
        parameter_ranges: dict[str, tuple[float, float]],
    ) -> dict[str, Any]:
        """¿Cuánto cambia cada output al variar cada parámetro? Sin implementar en V1."""
        ...
