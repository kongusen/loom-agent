"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import FilesystemWatchMethod, WatchKind


@dataclass(slots=True)
class ResourceThresholds:
    """Stable resource thresholds for heartbeat monitoring."""

    cpu_pct: float | None = None
    memory_pct: float | None = None
    disk_pct: float | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_runtime_config(self) -> dict[str, Any]:
        payload = dict(self.extensions)
        if self.cpu_pct is not None:
            payload["cpu_pct"] = self.cpu_pct
        if self.memory_pct is not None:
            payload["memory_pct"] = self.memory_pct
        if self.disk_pct is not None:
            payload["disk_pct"] = self.disk_pct
        return payload


@dataclass(slots=True)
class WatchConfig:
    """One heartbeat watch source."""

    kind: WatchKind
    paths: list[str] = field(default_factory=list)
    method: FilesystemWatchMethod | None = None
    pid_file: str | None = None
    watch_pids: list[int] = field(default_factory=list)
    thresholds: ResourceThresholds | None = None
    topics: list[str] = field(default_factory=list)
    event_bus: Any | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def filesystem(
        cls,
        *,
        paths: list[str],
        method: FilesystemWatchMethod = FilesystemWatchMethod.HASH,
        extensions: dict[str, Any] | None = None,
    ) -> WatchConfig:
        return cls(
            kind=WatchKind.FILESYSTEM,
            paths=list(paths),
            method=method,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def process(
        cls,
        *,
        pid_file: str | None = None,
        watch_pids: list[int] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> WatchConfig:
        return cls(
            kind=WatchKind.PROCESS,
            pid_file=pid_file,
            watch_pids=list(watch_pids or []),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def resource(
        cls,
        *,
        thresholds: ResourceThresholds,
        extensions: dict[str, Any] | None = None,
    ) -> WatchConfig:
        return cls(
            kind=WatchKind.RESOURCE,
            thresholds=thresholds,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def mf_events(
        cls,
        *,
        topics: list[str] | None = None,
        event_bus: Any | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> WatchConfig:
        return cls(
            kind=WatchKind.MF_EVENTS,
            topics=list(topics or []),
            event_bus=event_bus,
            extensions=dict(extensions or {}),
        )

    def to_runtime_config(self) -> dict[str, Any]:
        payload = dict(self.extensions)
        if self.paths:
            payload["paths"] = list(self.paths)
        if self.method is not None:
            payload["method"] = self.method.value
        if self.pid_file is not None:
            payload["pid_file"] = self.pid_file
        if self.watch_pids:
            payload["watch_pids"] = list(self.watch_pids)
        if self.thresholds is not None:
            payload["thresholds"] = self.thresholds.to_runtime_config()
        if self.topics:
            payload["topics"] = list(self.topics)
        if self.event_bus is not None:
            payload["event_bus"] = self.event_bus
        return payload


@dataclass(slots=True)
class HeartbeatInterruptPolicy:
    """Stable heartbeat interrupt behavior by urgency."""

    low: str = "queue"
    high: str = "request"
    critical: str = "force"
    extensions: dict[str, str] = field(default_factory=dict)

    def to_runtime_config(self) -> dict[str, str]:
        payload = {
            "low": self.low,
            "high": self.high,
            "critical": self.critical,
        }
        payload.update(self.extensions)
        return payload


@dataclass(slots=True)
class HeartbeatConfig:
    """Heartbeat configuration exposed on the public API."""

    interval: float = 5.0
    min_entropy_delta: float = 0.1
    watch_sources: list[WatchConfig] = field(default_factory=list)
    interrupt_policy: HeartbeatInterruptPolicy = field(default_factory=HeartbeatInterruptPolicy)
