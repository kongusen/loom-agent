"""Orchestration configuration for public Agent shortcuts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OrchestrationConfig:
    """Declarative shortcut for enabling Loom orchestration."""

    max_depth: int = 3
    delegation: Any | None = None
    planner: bool = True
    gen_eval: bool = False

    @classmethod
    def default(cls) -> OrchestrationConfig:
        return cls(max_depth=3, planner=True, gen_eval=False)

    @classmethod
    def full(cls, *, max_depth: int = 5) -> OrchestrationConfig:
        return cls(max_depth=max_depth, planner=True, gen_eval=True)
