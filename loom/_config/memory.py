"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MemoryBackend:
    """Stable memory backend definition."""

    name: str
    options: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def in_memory(
        cls,
        *,
        extensions: dict[str, Any] | None = None,
    ) -> MemoryBackend:
        return cls(name="in_memory", extensions=dict(extensions or {}))

    @classmethod
    def custom(
        cls,
        name: str,
        *,
        options: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> MemoryBackend:
        return cls(
            name=name,
            options=dict(options or {}),
            extensions=dict(extensions or {}),
        )


class MemoryProvider(ABC):
    """Pluggable long-term memory provider.

    Providers can contribute recalled context before a run and observe the
    completed user/assistant turn after the run.  Methods are synchronous for
    now to keep the provider contract simple; implementations that need network
    IO should cache/prefetch internally.
    """

    name: str = "custom"

    def is_available(self) -> bool:
        """Return whether this provider is configured and ready."""
        return True

    def system_prompt(self) -> str:
        """Optional static memory guidance appended to the system prompt."""
        return ""

    def prefetch(self, query: str, *, session_id: str | None = None) -> str:
        """Return recalled context for the next run."""
        _ = query, session_id
        return ""

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str | None = None,
    ) -> None:
        """Persist or learn from one completed turn."""
        _ = user_content, assistant_content, session_id


@dataclass(slots=True)
class MemoryConfig:
    """Session memory configuration."""

    enabled: bool = True
    backend: MemoryBackend = field(default_factory=MemoryBackend.in_memory)
    namespace: str | None = None
    providers: list[MemoryProvider] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
