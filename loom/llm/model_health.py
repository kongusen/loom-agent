"""US8: Model Health Checking

Tracks model health and enables intelligent fallback decisions.
"""

from __future__ import annotations

import time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class HealthStatus(str, Enum):
    """Model health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthMetrics:
    """Health metrics for a model."""
    status: HealthStatus
    success_count: int = 0
    failure_count: int = 0
    total_requests: int = 0
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    avg_latency_ms: float = 0.0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        return 1.0 - self.success_rate


class ModelHealthChecker:
    """Tracks and evaluates model health.

    Example:
        checker = ModelHealthChecker()

        # Record success
        checker.record_success("gpt-4", latency_ms=234.5)

        # Record failure
        checker.record_failure("gpt-4", error="timeout")

        # Check health
        status = checker.get_status("gpt-4")
        print(f"Model health: {status}")  # HEALTHY / DEGRADED / UNHEALTHY
    """

    def __init__(
        self,
        degraded_threshold: float = 0.8,  # <80% success rate = degraded
        unhealthy_threshold: float = 0.5,  # <50% success rate = unhealthy
        consecutive_failure_threshold: int = 5,  # 5 consecutive failures = unhealthy
        health_check_window: int = 100,  # Last 100 requests
    ):
        """Initialize health checker.

        Args:
            degraded_threshold: Success rate threshold for degraded status
            unhealthy_threshold: Success rate threshold for unhealthy status
            consecutive_failure_threshold: Consecutive failures to mark unhealthy
            health_check_window: Number of recent requests to consider
        """
        self.degraded_threshold = degraded_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.consecutive_failure_threshold = consecutive_failure_threshold
        self.health_check_window = health_check_window

        self._metrics: Dict[str, HealthMetrics] = {}
        self._latency_samples: Dict[str, list[float]] = {}  # Rolling window

    def record_success(
        self,
        model_id: str,
        latency_ms: float = 0.0
    ) -> None:
        """Record a successful request.

        Args:
            model_id: Model identifier
            latency_ms: Request latency in milliseconds
        """
        if model_id not in self._metrics:
            self._metrics[model_id] = HealthMetrics(status=HealthStatus.UNKNOWN)

        metrics = self._metrics[model_id]
        metrics.success_count += 1
        metrics.total_requests += 1
        metrics.last_success_time = time.time()
        metrics.consecutive_failures = 0

        # Update rolling latency
        if model_id not in self._latency_samples:
            self._latency_samples[model_id] = []

        self._latency_samples[model_id].append(latency_ms)

        # Keep only recent samples
        if len(self._latency_samples[model_id]) > self.health_check_window:
            self._latency_samples[model_id].pop(0)

        # Update average latency
        if self._latency_samples[model_id]:
            metrics.avg_latency_ms = sum(self._latency_samples[model_id]) / len(self._latency_samples[model_id])

        # Update status
        self._update_status(model_id)

    def record_failure(
        self,
        model_id: str,
        error: Optional[str] = None
    ) -> None:
        """Record a failed request.

        Args:
            model_id: Model identifier
            error: Error message
        """
        if model_id not in self._metrics:
            self._metrics[model_id] = HealthMetrics(status=HealthStatus.UNKNOWN)

        metrics = self._metrics[model_id]
        metrics.failure_count += 1
        metrics.total_requests += 1
        metrics.last_failure_time = time.time()
        metrics.consecutive_failures += 1

        # Update status
        self._update_status(model_id)

    def _update_status(self, model_id: str) -> None:
        """Update health status based on metrics.

        Args:
            model_id: Model identifier
        """
        metrics = self._metrics[model_id]

        # Check consecutive failures
        if metrics.consecutive_failures >= self.consecutive_failure_threshold:
            metrics.status = HealthStatus.UNHEALTHY
            return

        # Check success rate (only if we have enough data)
        if metrics.total_requests > 0:
            success_rate = metrics.success_rate

            if success_rate >= self.degraded_threshold:
                metrics.status = HealthStatus.HEALTHY
            elif success_rate >= self.unhealthy_threshold:
                metrics.status = HealthStatus.DEGRADED
            else:
                metrics.status = HealthStatus.UNHEALTHY
        else:
            metrics.status = HealthStatus.UNKNOWN

    def get_status(self, model_id: str) -> HealthStatus:
        """Get current health status.

        Args:
            model_id: Model identifier

        Returns:
            Current health status
        """
        if model_id not in self._metrics:
            return HealthStatus.UNKNOWN

        return self._metrics[model_id].status

    def get_metrics(self, model_id: str) -> Optional[HealthMetrics]:
        """Get detailed health metrics.

        Args:
            model_id: Model identifier

        Returns:
            HealthMetrics or None if not tracked
        """
        return self._metrics.get(model_id)

    def is_healthy(self, model_id: str) -> bool:
        """Check if model is healthy.

        Args:
            model_id: Model identifier

        Returns:
            True if healthy, False otherwise
        """
        status = self.get_status(model_id)
        return status == HealthStatus.HEALTHY

    def get_all_healthy_models(self) -> list[str]:
        """Get list of all healthy models.

        Returns:
            List of model IDs with healthy status
        """
        return [
            model_id
            for model_id, metrics in self._metrics.items()
            if metrics.status == HealthStatus.HEALTHY
        ]

    def reset(self, model_id: Optional[str] = None) -> None:
        """Reset health metrics.

        Args:
            model_id: Model to reset (None = reset all)
        """
        if model_id:
            if model_id in self._metrics:
                self._metrics[model_id] = HealthMetrics(status=HealthStatus.UNKNOWN)
            if model_id in self._latency_samples:
                self._latency_samples[model_id] = []
        else:
            self._metrics.clear()
            self._latency_samples.clear()
