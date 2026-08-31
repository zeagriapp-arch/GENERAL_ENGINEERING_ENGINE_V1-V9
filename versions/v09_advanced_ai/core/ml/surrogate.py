"""
Scientific Machine Learning — interfaces preparadas, SIN implementación
(sección 27, Phase 9): "No implementar todas estas tecnologías en V1.
Crear interfaces para que puedan incorporarse posteriormente."

Pipeline previsto (cuando exista suficiente Experiment Memory):
    Physical Simulator -> Dataset -> ML Surrogate -> Fast Prediction
    -> Candidate Filtering -> Physical Simulation Validation

Principio que cualquier implementación futura DEBE respetar: "El modelo
ML nunca debe sustituir automáticamente al simulador físico sin
validación" — un SurrogateModel puede filtrar/priorizar candidatos más
rápido, pero el resultado final siempre pasa por PhysicsModel/
SimulationSolver antes de aceptarse (mismo patrón que ya usan
DesignEngine y Optimizer con `evaluate_requirements`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.experiments.schema import Experiment


class SurrogateModel(ABC):
    """Aproximación rápida de un PhysicsModel, entrenada sobre Experiments ya validados."""

    @abstractmethod
    def fit(self, experiments: list[Experiment]) -> None:
        """Entrena el surrogate sobre resultados YA validados físicamente — nunca sobre sus propias predicciones."""
        ...

    @abstractmethod
    def predict(self, inputs: dict[str, float]) -> dict[str, Any]:
        """
        Predicción rápida, NO validada. El caller es responsable de no
        tratar esto como `Results` real — solo sirve para filtrar
        candidatos antes de la simulación física real.
        """
        ...


class ActiveLearningStrategy(ABC):
    """Decide qué próximos puntos simular físicamente para mejorar el surrogate lo más rápido posible."""

    @abstractmethod
    def suggest_next_points(
        self, surrogate: SurrogateModel, n: int, *, search_space: dict[str, tuple[float, float]]
    ) -> list[dict[str, float]]:
        ...
