"""
OllamaProvider: implementación concreta de ModelProvider sobre la API de
Ollama (/api/chat). Es la única clase de todo el sistema que sabe que
"Ollama" existe — todo lo demás habla con `ModelProvider` (interfaz).

Nota: esta clase NO se ejercita contra un servidor real en los tests de
Phase 1 (no hay Ollama corriendo en este entorno) — los tests de
Orchestrator/Agents usan un `FakeModelProvider` (tests/unit y
tests/integration). Esta implementación se valida en Phase 6 cuando se
integren los agentes reales contra un Ollama local.
"""
from __future__ import annotations

import json

import httpx
from pydantic import BaseModel, ValidationError

from config.settings import ModelsConfig
from core.models.interfaces import ModelProvider, ModelResponse, ToolSpec


class OllamaResponseValidationError(ValueError):
    pass


class OllamaProvider(ModelProvider):
    def __init__(self, config: ModelsConfig, *, client: httpx.AsyncClient | None = None):
        self._config = config
        self._client = client or httpx.AsyncClient(
            base_url=config.ollama.endpoint, timeout=config.ollama.timeout_seconds
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        role: str = "reasoning",
        response_schema: type[BaseModel] | None = None,
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse:
        model_cfg = self._config.resolve(role)

        payload: dict = {
            "model": model_cfg.model,
            "messages": messages,
            "stream": False,
        }
        if response_schema is not None:
            payload["format"] = response_schema.model_json_schema()
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters_schema,
                    },
                }
                for t in tools
            ]

        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        message = data.get("message", {})
        text = message.get("content")
        tool_calls = message.get("tool_calls", [])

        structured = None
        if response_schema is not None and text:
            try:
                structured = json.loads(text)
                response_schema.model_validate(structured)
            except (json.JSONDecodeError, ValidationError) as exc:
                raise OllamaResponseValidationError(
                    f"Ollama devolvió una salida que no valida contra "
                    f"{response_schema.__name__}: {exc}"
                ) from exc

        return ModelResponse(text=text, structured=structured, tool_calls=tool_calls, raw=data)
