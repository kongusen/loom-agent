"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class GenerationConfig:
    """Stable model generation controls."""

    temperature: float = 0.7
    max_output_tokens: int | None = None
    extensions: dict[str, Any] = field(default_factory=dict)
