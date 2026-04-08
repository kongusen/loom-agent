"""Result types for Agent operations"""

from dataclasses import dataclass
from typing import Any

from .state import LoopState


@dataclass
class LoopResult:
    """L* loop execution result"""
    state: LoopState
    output: Any = None
    should_continue: bool = True
    error: str | None = None
    reason: str | None = None  # Decision reason from DecisionEngine


@dataclass
class SubAgentResult:
    """Sub-Agent execution result"""
    success: bool
    output: Any
    depth: int
    error: str | None = None
