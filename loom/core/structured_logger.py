"""US7: Structured Logging with Correlation IDs

Provides JSON-formatted structured logging for production observability.

Features:
- Correlation ID tracking across requests
- JSON format for log aggregation tools (Datadog, CloudWatch, etc.)
- Context propagation
- Performance metrics
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar


# Context variable for correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredLogger:
    """Structured logger with correlation ID support.

    Example:
        logger = StructuredLogger("my_agent")

        # Set correlation ID for request
        logger.set_correlation_id("req-123")

        # All logs include correlation_id
        logger.info("Processing request", user_id="user_456")
        # Output: {"timestamp": "...", "level": "INFO", "message": "Processing request",
        #          "correlation_id": "req-123", "user_id": "user_456"}
    """

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        include_timestamp: bool = True,
        include_location: bool = True,
    ):
        """Initialize structured logger.

        Args:
            name: Logger name (usually module or component name)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            include_timestamp: Include ISO timestamp in logs
            include_location: Include file location in logs
        """
        self.name = name
        self.level = level
        self.include_timestamp = include_timestamp
        self.include_location = include_location
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for current context.

        Args:
            correlation_id: Unique identifier for request/conversation
        """
        _correlation_id.set(correlation_id)

    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID."""
        return _correlation_id.get()

    def clear_correlation_id(self) -> None:
        """Clear correlation ID from context."""
        _correlation_id.set(None)

    def _format_log(
        self,
        level: str,
        message: str,
        extra: Dict[str, Any],
        exc_info: Optional[Exception] = None,
    ) -> Dict[str, Any]:
        """Format log entry as JSON-serializable dict.

        Args:
            level: Log level string
            message: Log message
            extra: Additional context fields
            exc_info: Exception info if available

        Returns:
            JSON-serializable dict
        """
        log_entry = {
            "level": level,
            "message": message,
            "logger": self.name,
        }

        # Add timestamp
        if self.include_timestamp:
            log_entry["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add correlation ID if available
        correlation_id = self.get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add extra fields
        if extra:
            log_entry.update(extra)

        # Add exception info
        if exc_info:
            log_entry["exception"] = {
                "type": type(exc_info).__name__,
                "message": str(exc_info),
            }

        return log_entry

    def _log(
        self,
        level: int,
        level_name: str,
        message: str,
        exc_info: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Internal logging method.

        Args:
            level: Logging level constant
            level_name: Level name string
            message: Log message
            exc_info: Exception if available
            **kwargs: Additional context fields
        """
        if self._logger.isEnabledFor(level):
            log_entry = self._format_log(level_name, message, kwargs, exc_info)

            # Output as JSON
            json_log = json.dumps(log_entry, default=str)

            # Use standard logger
            self._logger.log(level, json_log)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, "DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, "INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, "WARNING", message, **kwargs)

    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, "ERROR", message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: Optional[Exception] = None, **kwargs: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, "CRITICAL", message, exc_info=exc_info, **kwargs)

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **kwargs: Any,
    ) -> None:
        """Log performance metrics.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            **kwargs: Additional metrics
        """
        self.info(
            "Performance metric",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            **kwargs,
        )


class PerformanceTimer:
    """Context manager for timing operations.

    Example:
        logger = StructuredLogger("my_agent")

        with PerformanceTimer(logger, "llm_call") as timer:
            result = await llm.generate(prompt)

        # Automatically logs: {"operation": "llm_call", "duration_ms": 234.5, ...}
    """

    def __init__(
        self,
        logger: StructuredLogger,
        operation: str,
        log_level: str = "info",
        **extra_context: Any,
    ):
        """Initialize performance timer.

        Args:
            logger: StructuredLogger instance
            operation: Operation name
            log_level: Log level for performance metric
            **extra_context: Additional context to include
        """
        self.logger = logger
        self.operation = operation
        self.log_level = log_level
        self.extra_context = extra_context
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def __enter__(self):
        """Start timer."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and log performance."""
        self.end_time = time.time()

        if self.start_time is not None:
            duration_ms = (self.end_time - self.start_time) * 1000
            success = exc_type is None

            self.logger.log_performance(
                self.operation,
                duration_ms,
                success=success,
                **self.extra_context,
            )

        return False  # Don't suppress exceptions


# Global logger instance
_default_logger = StructuredLogger("loom")


def get_logger(name: str = "loom") -> StructuredLogger:
    """Get or create a structured logger.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context (convenience function).

    Args:
        correlation_id: Unique identifier
    """
    _correlation_id.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID (convenience function)."""
    return _correlation_id.get()
