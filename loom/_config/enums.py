"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from enum import StrEnum


class WatchKind(StrEnum):
    """Supported public heartbeat watch kinds."""

    FILESYSTEM = "filesystem"
    PROCESS = "process"
    RESOURCE = "resource"
    MF_EVENTS = "mf_events"


class FilesystemWatchMethod(StrEnum):
    """Supported filesystem watch strategies."""

    HASH = "hash"


class RuntimeFallbackMode(StrEnum):
    """Supported runtime fallback behaviors."""

    LOCAL_SUMMARY = "local_summary"
    ERROR = "error"
