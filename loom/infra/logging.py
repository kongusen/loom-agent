"""
Structured Logging Configuration.
"""

import logging
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", json_format: bool = False) -> None:
    """
    Configure standard logging and structlog.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure processors
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """
    Get a structured logger.
    """
    return structlog.get_logger(name)
