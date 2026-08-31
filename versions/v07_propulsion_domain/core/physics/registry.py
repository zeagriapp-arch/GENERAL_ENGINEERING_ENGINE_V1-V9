"""
PhysicsModelRegistry: selecciona el PhysicsModel aplicable a un Design
dado. NO importa nada de `domains/` — los modelos concretos se registran
desde fuera (wiring de aplicación), preservando la regla core ↛ domains.
"""
from __future__ import annotations

from core.design.schema import Design
from core.physics.interfaces import PhysicsModel


class NoPhysicsModelAvailableError(LookupError):
    pass


class PhysicsModelRegistry:
    def __init__(self):
        self._models: list[PhysicsModel] = []

    def register(self, model: PhysicsModel) -> None:
        self._models.append(model)

    def select(self, design: Design) -> PhysicsModel:
        for model in self._models:
            if model.applies_to(design):
                return model
        raise NoPhysicsModelAvailableError(
            f"Ningún PhysicsModel registrado aplica a Design {design.id} (domain={design.domain})."
        )
