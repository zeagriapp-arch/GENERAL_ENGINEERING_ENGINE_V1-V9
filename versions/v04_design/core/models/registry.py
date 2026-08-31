"""
ModelRegistry (sección 25): mapea roles lógicos -> modelo concreto,
leído de config/models.yaml. Nada de negocio hardcodea nombres de modelo.
"""
from __future__ import annotations

from config.settings import ModelRoleConfig, Settings
from core.models.interfaces import ModelProvider


class ModelRegistry:
    def __init__(self, settings: Settings, provider: ModelProvider):
        self._settings = settings
        self._provider = provider

    def resolve_config(self, role: str) -> ModelRoleConfig:
        return self._settings.models.resolve(role)

    @property
    def provider(self) -> ModelProvider:
        """El ModelProvider concreto (ej. OllamaProvider) a usar para cualquier rol."""
        return self._provider

    def available_roles(self) -> list[str]:
        return list(self._settings.models.roles)
