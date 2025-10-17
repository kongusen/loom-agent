"""US7: Observability Callbacks

Enhanced callbacks for production observability and monitoring.

New event types:
- compression_start: Before context compression
- compression_complete: After compression with metrics
- subagent_spawned: When sub-agent is created
- subagent_completed: When sub-agent finishes
- retry_attempt: When operation is retried
- circuit_breaker_opened: When circuit opens
- circuit_breaker_closed: When circuit closes
- performance_metric: General performance tracking
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from loom.callbacks.base import BaseCallback
from loom.core.structured_logger import StructuredLogger


class ObservabilityCallback(BaseCallback):
    """Callback for structured logging and observability.

    Logs all agent events in JSON format for aggregation.

    Example:
        logger = StructuredLogger("my_agent")
        callback = ObservabilityCallback(logger)

        agent = Agent(llm=llm, callbacks=[callback])
    """

    def __init__(
        self,
        logger: Optional[StructuredLogger] = None,
        log_all_events: bool = True,
        log_performance: bool = True,
    ):
        """Initialize observability callback.

        Args:
            logger: StructuredLogger instance (creates one if None)
            log_all_events: Log all events (default True)
            log_performance: Log performance metrics separately (default True)
        """
        if logger is None:
            logger = StructuredLogger("loom.observability")

        self.logger = logger
        self.log_all_events = log_all_events
        self.log_performance = log_performance

    async def on_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Handle agent events.

        Args:
            event_type: Event type string
            payload: Event payload
        """
        # Extract correlation ID if available
        correlation_id = payload.get("correlation_id")
        if correlation_id and not self.logger.get_correlation_id():
            self.logger.set_correlation_id(correlation_id)

        # Log all events if enabled
        if self.log_all_events:
            self.logger.info(
                f"Agent event: {event_type}",
                event_type=event_type,
                **payload
            )

        # Special handling for specific events
        if event_type == "compression_start":
            self._log_compression_start(payload)
        elif event_type == "compression_complete":
            self._log_compression_complete(payload)
        elif event_type == "subagent_spawned":
            self._log_subagent_spawned(payload)
        elif event_type == "retry_attempt":
            self._log_retry_attempt(payload)
        elif event_type == "error":
            self._log_error(payload)
        elif event_type in ["llm_call", "tool_call"] and self.log_performance:
            self._log_performance(event_type, payload)

    def _log_compression_start(self, payload: Dict[str, Any]) -> None:
        """Log compression start event."""
        self.logger.info(
            "Context compression starting",
            token_count=payload.get("token_count"),
            message_count=payload.get("message_count"),
        )

    def _log_compression_complete(self, payload: Dict[str, Any]) -> None:
        """Log compression completion with metrics."""
        before_tokens = payload.get("before_tokens", 0)
        after_tokens = payload.get("after_tokens", 0)
        ratio = payload.get("compression_ratio", 0)

        self.logger.log_performance(
            "context_compression",
            duration_ms=payload.get("duration_ms", 0),
            success=True,
            before_tokens=before_tokens,
            after_tokens=after_tokens,
            compression_ratio=ratio,
            tokens_saved=before_tokens - after_tokens,
        )

    def _log_subagent_spawned(self, payload: Dict[str, Any]) -> None:
        """Log sub-agent spawn event."""
        self.logger.info(
            "Sub-agent spawned",
            subagent_id=payload.get("subagent_id"),
            execution_depth=payload.get("execution_depth"),
            tool_whitelist=payload.get("tool_whitelist"),
        )

    def _log_retry_attempt(self, payload: Dict[str, Any]) -> None:
        """Log retry attempt."""
        self.logger.warning(
            "Retry attempt",
            attempt=payload.get("attempt"),
            max_attempts=payload.get("max_attempts"),
            operation=payload.get("operation"),
            error=payload.get("error"),
        )

    def _log_error(self, payload: Dict[str, Any]) -> None:
        """Log error with context."""
        self.logger.error(
            f"Agent error in {payload.get('stage', 'unknown')}",
            stage=payload.get("stage"),
            message=payload.get("message"),
            iteration=payload.get("iteration"),
        )

    def _log_performance(self, operation: str, payload: Dict[str, Any]) -> None:
        """Log performance metric."""
        duration_ms = payload.get("duration_ms", 0)
        if duration_ms > 0:
            self.logger.log_performance(
                operation,
                duration_ms,
                success=True,
                **payload
            )


class MetricsAggregator(BaseCallback):
    """Aggregates metrics for monitoring dashboards.

    Example:
        aggregator = MetricsAggregator()
        agent = Agent(llm=llm, callbacks=[aggregator])

        # After running agent
        summary = aggregator.get_summary()
        print(f"Total LLM calls: {summary['llm_calls']}")
        print(f"Avg LLM latency: {summary['avg_llm_latency_ms']:.2f}ms")
    """

    def __init__(self):
        """Initialize metrics aggregator."""
        self.metrics = {
            "llm_calls": 0,
            "llm_total_ms": 0.0,
            "tool_calls": 0,
            "tool_total_ms": 0.0,
            "compressions": 0,
            "compression_total_ms": 0.0,
            "errors": 0,
            "subagents_spawned": 0,
            "retry_attempts": 0,
        }
        self.start_time = datetime.now()

    async def on_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Aggregate metrics from events."""
        if event_type == "llm_call":
            self.metrics["llm_calls"] += 1
            self.metrics["llm_total_ms"] += payload.get("duration_ms", 0)

        elif event_type == "tool_call":
            self.metrics["tool_calls"] += 1
            self.metrics["tool_total_ms"] += payload.get("duration_ms", 0)

        elif event_type == "compression_complete":
            self.metrics["compressions"] += 1
            self.metrics["compression_total_ms"] += payload.get("duration_ms", 0)

        elif event_type == "error":
            self.metrics["errors"] += 1

        elif event_type == "subagent_spawned":
            self.metrics["subagents_spawned"] += 1

        elif event_type == "retry_attempt":
            self.metrics["retry_attempts"] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get aggregated metrics summary.

        Returns:
            Dict with summary statistics
        """
        elapsed_seconds = (datetime.now() - self.start_time).total_seconds()

        summary = {
            **self.metrics,
            "uptime_seconds": elapsed_seconds,
        }

        # Calculate averages
        if self.metrics["llm_calls"] > 0:
            summary["avg_llm_latency_ms"] = (
                self.metrics["llm_total_ms"] / self.metrics["llm_calls"]
            )

        if self.metrics["tool_calls"] > 0:
            summary["avg_tool_latency_ms"] = (
                self.metrics["tool_total_ms"] / self.metrics["tool_calls"]
            )

        if self.metrics["compressions"] > 0:
            summary["avg_compression_ms"] = (
                self.metrics["compression_total_ms"] / self.metrics["compressions"]
            )

        # Calculate rates (per minute)
        if elapsed_seconds > 0:
            minutes = elapsed_seconds / 60
            summary["llm_calls_per_minute"] = self.metrics["llm_calls"] / minutes
            summary["errors_per_minute"] = self.metrics["errors"] / minutes

        return summary

    def reset(self) -> None:
        """Reset all metrics."""
        for key in self.metrics:
            if isinstance(self.metrics[key], (int, float)):
                self.metrics[key] = 0
        self.start_time = datetime.now()
