"""
ModelProvider (sección 5): única abstracción que agentes/orchestrator
conocen para hablar con un LLM. Cambiar de proveedor (Ollama -> otro)
implica escribir una nueva clase que implemente esta interfaz, sin tocar
ningún agente.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters_schema: dict[str, Any] = {}


class ModelResponse(BaseModel):
    text: str | None = None
    structured: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}


class ModelProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        role: str = "reasoning",
        response_schema: type[BaseModel] | None = None,
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse:
        """
        Ejecuta una llamada al modelo asociado al `role` (resuelto vía
        ModelRegistry, nunca hardcodeado). Si `response_schema` se
        provee, la implementación DEBE validar la salida contra ese
        schema antes de devolverla (structured output).
        """
        ...

    async def embed(self, texts: list[str], *, role: str = "embeddings") -> list[list[float]]:
        """
        Produce embeddings para `texts` usando el modelo asociado al rol
        'embeddings'. No es abstracto (default: NotImplementedError) para
        no romper implementaciones/mocks de Phase 1 que no lo necesitan
        (ej. FakeModelProvider en tests de reasoning). Cualquier
        ModelProvider pensado para el Knowledge Engine (ej.
        OllamaProvider) SÍ lo implementa.
        """
        raise NotImplementedError(f"{type(self).__name__} no implementa embed().")
