"""
Agent base (secciones 6, 24, 38, 39).

Cada agente concreto declara `name` (debe coincidir con las claves
`allowed_agents` de config/tools.yaml — el ToolRegistry rechaza en
runtime cualquier invocación fuera de esa lista, no solo por
convención). `ask()` fuerza salida estructurada validada contra un
schema Pydantic — un agente nunca puede devolver texto libre sin
parsear como si fuera un resultado.
"""
from __future__ import annotations

from abc import ABC
from typing import TypeVar

from pydantic import BaseModel

from core.models.interfaces import ToolSpec
from core.models.registry import ModelRegistry
from core.tools.interfaces import ToolProvider, ToolResult

T = TypeVar("T", bound=BaseModel)


class AgentResponseError(ValueError):
    pass


class Agent(ABC):
    name: str

    def __init__(self, model_registry: ModelRegistry, tool_registry: ToolProvider, *, role: str = "reasoning"):
        self._models = model_registry
        self._tools = tool_registry
        self._role = role

    def available_tools(self) -> list[ToolSpec]:
        return self._tools.get_tools_for_agent(self.name)

    async def invoke_tool(self, tool_name: str, args: dict) -> ToolResult:
        """Delega en ToolRegistry — que valida permisos en runtime, no aquí."""
        return await self._tools.invoke(tool_name, args, caller=self.name)

    async def ask(self, messages: list[dict[str, str]], response_schema: type[T]) -> T:
        response = await self._models.provider.complete(
            messages, role=self._role, response_schema=response_schema, tools=self.available_tools()
        )
        if response.structured is None:
            raise AgentResponseError(
                f"{self.name}: el modelo no devolvió salida estructurada válida para {response_schema.__name__}."
            )
        return response_schema.model_validate(response.structured)
