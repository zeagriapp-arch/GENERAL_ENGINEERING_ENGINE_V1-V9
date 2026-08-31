"""
Config loader central. Todo lo que puede cambiar vive en YAML (sección 37),
nunca hardcodeado en el código de negocio.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

CONFIG_DIR = Path(__file__).parent


class ModelRoleConfig(BaseModel):
    model: str
    provider: str
    context_size: int
    intended_use: str


class OllamaConfig(BaseModel):
    endpoint: str
    timeout_seconds: int


class ModelsConfig(BaseModel):
    provider_default: str
    roles: dict[str, ModelRoleConfig]
    ollama: OllamaConfig

    def resolve(self, role: str) -> ModelRoleConfig:
        if role not in self.roles:
            raise KeyError(
                f"Rol de modelo '{role}' no está registrado en models.yaml. "
                f"Roles disponibles: {list(self.roles)}"
            )
        return self.roles[role]


class ToolSpecConfig(BaseModel):
    handler: str
    description: str
    allowed_agents: list[str]


class ToolsConfig(BaseModel):
    tools: dict[str, ToolSpecConfig]


class BudgetConfig(BaseModel):
    max_iterations: int
    max_simulations: int
    max_llm_calls: int
    max_runtime_seconds: int
    max_research_calls: int


class BudgetsConfig(BaseModel):
    default: BudgetConfig
    stopping_criteria: list[str]


class Settings(BaseModel):
    models: ModelsConfig
    tools: ToolsConfig
    budgets: BudgetsConfig
    db_path: str = Field(default_factory=lambda: str(Path("gede.db").resolve()))


def _load_yaml(name: str) -> dict:
    path = CONFIG_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        models=ModelsConfig(**_load_yaml("models.yaml")),
        tools=ToolsConfig(**_load_yaml("tools.yaml")),
        budgets=BudgetsConfig(**_load_yaml("budgets.yaml")),
    )
