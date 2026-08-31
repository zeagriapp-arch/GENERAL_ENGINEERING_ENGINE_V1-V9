"""
ScriptedModelProvider: ModelProvider determinista para tests de agentes,
sin depender de un servidor Ollama real. Cada rol tiene una cola de
respuestas estructuradas que se van consumiendo en orden.
"""
from __future__ import annotations

import json

import pytest

from core.models.interfaces import ModelProvider, ModelResponse


class ScriptedModelProvider(ModelProvider):
    def __init__(self, responses: dict[str, list[dict]] | None = None):
        self._responses: dict[str, list[dict]] = {k: list(v) for k, v in (responses or {}).items()}
        self.calls: list[dict] = []

    def queue(self, role: str, response: dict) -> None:
        self._responses.setdefault(role, []).append(response)

    async def complete(self, messages, *, role="reasoning", response_schema=None, tools=None):
        self.calls.append({"role": role, "messages": messages, "tools": tools})
        if role not in self._responses or not self._responses[role]:
            raise RuntimeError(f"ScriptedModelProvider: no queda respuesta guionizada para role='{role}'.")
        structured = self._responses[role].pop(0)
        return ModelResponse(text=json.dumps(structured), structured=structured, tool_calls=[], raw={})

    async def embed(self, texts, *, role="embeddings"):
        raise NotImplementedError


@pytest.fixture
def scripted_provider():
    return ScriptedModelProvider()
