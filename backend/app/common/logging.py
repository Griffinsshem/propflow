"""Structured logging: readable console output in development, JSON elsewhere."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger

SERVICE_NAME = "propflow-api"


def _add_service(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    event_dict.setdefault("service", SERVICE_NAME)
    return event_dict


def configure_logging(app_env: str) -> None:
    level = logging.DEBUG if app_env == "development" else logging.INFO
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_service,
    ]
    if app_env == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors += [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer()]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
