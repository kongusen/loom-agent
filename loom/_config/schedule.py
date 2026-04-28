"""Schedule configuration for lightweight in-process cron support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from importlib import import_module
from typing import Any, Literal


@dataclass(slots=True)
class ScheduleConfig:
    """Declarative schedule for one in-memory job."""

    kind: Literal["once", "interval", "cron"]
    interval_minutes: int | None = None
    run_at: str | None = None
    cron_expr: str | None = None

    @classmethod
    def once(cls, run_at: str | datetime) -> ScheduleConfig:
        return cls(kind="once", run_at=_serialize_datetime(run_at))

    @classmethod
    def interval(
        cls,
        *,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
    ) -> ScheduleConfig:
        total_minutes = minutes + hours * 60 + days * 24 * 60
        if total_minutes <= 0:
            raise ValueError("interval schedule requires a positive duration")
        return cls(kind="interval", interval_minutes=total_minutes)

    @classmethod
    def cron(cls, expr: str) -> ScheduleConfig:
        try:
            import_module("croniter")
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise ImportError("ScheduleConfig.cron() requires optional dependency 'croniter'") from exc
        if not expr.strip():
            raise ValueError("cron expression must not be empty")
        return cls(kind="cron", cron_expr=expr)

    def compute_next_run(self, last_run_at: datetime | None = None) -> datetime | None:
        if self.kind == "once":
            if last_run_at is not None:
                return None
            if self.run_at is None:
                raise ValueError("once schedule requires run_at")
            return _parse_datetime(self.run_at)

        if self.kind == "interval":
            if self.interval_minutes is None or self.interval_minutes <= 0:
                raise ValueError("interval schedule requires positive interval_minutes")
            base = last_run_at or datetime.now()
            return base + timedelta(minutes=self.interval_minutes)

        if self.kind == "cron":
            if not self.cron_expr:
                raise ValueError("cron schedule requires cron_expr")
            try:
                croniter_fn = import_module("croniter").croniter
            except ImportError as exc:  # pragma: no cover - depends on optional package
                raise ImportError(
                    "cron schedules require optional dependency 'croniter'"
                ) from exc
            next_run = croniter_fn(self.cron_expr, last_run_at or datetime.now()).get_next(
                datetime
            )
            if not isinstance(next_run, datetime):
                raise TypeError("croniter returned a non-datetime next run")
            return next_run

        raise ValueError(f"unknown schedule kind: {self.kind}")

    def is_due(self, next_run_at: datetime | None) -> bool:
        return next_run_at is not None and next_run_at <= datetime.now()


@dataclass(slots=True)
class ScheduledJob:
    """One in-memory scheduled prompt."""

    id: str
    prompt: str
    schedule: ScheduleConfig
    name: str = ""
    enabled: bool = True
    repeat: int | None = None
    completed: int = 0
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _serialize_datetime(value: str | datetime) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if not isinstance(value, str):
        raise TypeError(f"run_at must be str or datetime, got {type(value).__name__}")
    return value


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("run_at must be an ISO datetime string") from exc
