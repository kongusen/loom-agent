"""In-process scheduling primitives for Loom runtime signals."""

from __future__ import annotations

import builtins
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime

from .._config.schedule import ScheduledJob

logger = logging.getLogger(__name__)


class JobRegistry:
    """Thread-safe in-memory job registry."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, ScheduledJob] = {}

    def add(self, job: ScheduledJob) -> ScheduledJob:
        with self._lock:
            if job.next_run_at is None:
                job.next_run_at = job.schedule.compute_next_run(job.last_run_at)
            self._jobs[job.id] = job
            return job

    def remove(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs.pop(job_id, None) is not None

    def get(self, job_id: str) -> ScheduledJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> builtins.list[ScheduledJob]:
        with self._lock:
            return list(self._jobs.values())

    def get_due(self) -> builtins.list[ScheduledJob]:
        with self._lock:
            return [
                job
                for job in self._jobs.values()
                if job.enabled and job.schedule.is_due(job.next_run_at)
            ]

    def mark_ran(self, job_id: str, *, success: bool = True) -> None:
        _ = success
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            now = datetime.now()
            job.last_run_at = now
            job.completed += 1
            if job.repeat is not None and job.completed >= job.repeat:
                job.enabled = False
                job.next_run_at = None
                return
            job.next_run_at = job.schedule.compute_next_run(now)


class ScheduleTicker:
    """Daemon ticker that dispatches due jobs."""

    def __init__(self, registry: JobRegistry, *, interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.registry = registry
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread: threading.Thread | None = None
        self._dispatch: Callable[[ScheduledJob], None] | None = None

    def start(self, dispatch: Callable[[ScheduledJob], None]) -> None:
        if self.running:
            return
        self._dispatch = dispatch
        self.running = True
        self.thread = threading.Thread(target=self._tick_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=max(self.interval_seconds * 2, 1.0))

    def _tick_loop(self) -> None:
        while self.running:
            for job in self.registry.get_due():
                success = True
                try:
                    if self._dispatch is not None:
                        self._dispatch(job)
                except Exception as exc:  # pragma: no cover - defensive path
                    success = False
                    logger.warning("Scheduled job %s dispatch failed: %s", job.id, exc)
                finally:
                    self.registry.mark_ran(job.id, success=success)
            time.sleep(self.interval_seconds)
