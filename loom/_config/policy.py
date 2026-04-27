"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tools import ToolPolicy


@dataclass(slots=True)
class PolicyContext:
    """Stable policy execution context."""

    name: str = "default"
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def default(
        cls,
        *,
        extensions: dict[str, Any] | None = None,
    ) -> PolicyContext:
        return cls(name="default", extensions=dict(extensions or {}))

    @classmethod
    def named(
        cls,
        name: str,
        *,
        extensions: dict[str, Any] | None = None,
    ) -> PolicyContext:
        return cls(name=name, extensions=dict(extensions or {}))


@dataclass(slots=True)
class PolicyConfig:
    """Top-level policy configuration for one agent."""

    tools: ToolPolicy = field(default_factory=ToolPolicy)
    context: PolicyContext = field(default_factory=PolicyContext.default)
    extensions: dict[str, Any] = field(default_factory=dict)
