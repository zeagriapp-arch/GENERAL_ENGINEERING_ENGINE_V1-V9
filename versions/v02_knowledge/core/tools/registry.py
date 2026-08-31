"""
Tool Registry (sección 24). Carga config/tools.yaml y hace cumplir en
RUNTIME qué agente puede invocar qué tool — no es solo una convención de
prompt: `invoke()` rechaza cualquier llamada fuera de `allowed_agents`.
"""
from __future__ import annotations

import importlib
from typing import Any, Callable

from config.settings import ToolsConfig
from core.models.interfaces import ToolSpec
from core.tools.interfaces import ToolNotFoundError, ToolPermissionError, ToolProvider, ToolResult


def _resolve_handler(handler_path: str) -> Callable:
    """'core.knowledge.engine:search' -> función `search` del módulo."""
    module_path, func_name = handler_path.split(":")
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


class ToolRegistry(ToolProvider):
    def __init__(self, config: ToolsConfig):
        self._config = config

    def get_tools_for_agent(self, agent_name: str) -> list[ToolSpec]:
        result = []
        for name, spec in self._config.tools.items():
            if agent_name in spec.allowed_agents:
                result.append(ToolSpec(name=name, description=spec.description, parameters_schema={}))
        return result

    async def invoke(self, tool_name: str, args: dict[str, Any], *, caller: str) -> ToolResult:
        if tool_name not in self._config.tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' no está registrada en config/tools.yaml.")

        spec = self._config.tools[tool_name]
        if caller not in spec.allowed_agents:
            raise ToolPermissionError(
                f"'{caller}' no tiene permiso para invocar '{tool_name}'. "
                f"Agentes autorizados: {spec.allowed_agents}"
            )

        try:
            handler = _resolve_handler(spec.handler)
        except (ImportError, AttributeError) as exc:
            return ToolResult(ok=False, error=f"Handler '{spec.handler}' no disponible todavía: {exc}")

        try:
            if callable(handler):
                import inspect

                if inspect.iscoroutinefunction(handler):
                    value = await handler(**args)
                else:
                    value = handler(**args)
            return ToolResult(ok=True, value=value)
        except Exception as exc:  # el caller decide qué hacer con el error, no se oculta
            return ToolResult(ok=False, error=str(exc))
