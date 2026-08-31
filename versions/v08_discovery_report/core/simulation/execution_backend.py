"""
ExecutionBackend (sección 33): interfaz preparada para
sequential/multiprocessing/distributed/GPU. V1 solo implementa
`SequentialExecutionBackend` — el resto son extensiones futuras detrás
de la misma interfaz, sin infraestructura distribuida todavía
(sección 33 explícita: "No implementar infraestructura distribuida
compleja en V1").
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class ExecutionBackend(ABC):
    @abstractmethod
    def execute(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any: ...


class SequentialExecutionBackend(ExecutionBackend):
    """Único backend implementado en V1: ejecución directa, sin paralelismo."""

    def execute(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)


# Multiprocessing/distributed/GPU: Phase 9+ (Scientific ML / rendimiento),
# cuando profiling demuestre necesidad real (sección 34/46).
