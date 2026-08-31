from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.models.interfaces import ToolSpec


class ToolPermissionError(PermissionError):
    pass


class ToolNotFoundError(KeyError):
    pass


class ToolResult:
    def __init__(self, ok: bool, value: Any = None, error: str | None = None):
        self.ok = ok
        self.value = value
        self.error = error


class ToolProvider(ABC):
    @abstractmethod
    def get_tools_for_agent(self, agent_name: str) -> list[ToolSpec]: ...

    @abstractmethod
    async def invoke(self, tool_name: str, args: dict[str, Any], *, caller: str) -> ToolResult: ...
