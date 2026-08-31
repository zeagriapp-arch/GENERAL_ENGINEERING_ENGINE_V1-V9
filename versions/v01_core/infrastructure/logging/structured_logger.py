"""
Logging estructurado (JSON) para poder reconstruir qué ocurrió en una
ejecución: agent actions, tool calls, model calls, simulation calls,
parameters, errors, decisions, iteration number, experiment ID.
(Sección 33 de la especificación)
"""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: int = logging.INFO) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(**bind) -> structlog.BoundLogger:
    """Logger con contexto opcional pre-vinculado (ej. experiment_id)."""
    return structlog.get_logger().bind(**bind)
