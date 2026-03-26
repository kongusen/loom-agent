"""Evolution types for Axiom 4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TaskResult:
    """任务执行结果"""

    task: str
    success: bool
    trace: list[str]
    metadata: dict[str, Any]


@dataclass
class Pattern:
    """成功模式"""

    name: str
    frequency: int
    success_rate: float
    steps: list[str]


@dataclass
class FailureRecord:
    """失败记录"""

    task: str
    reason: str
    trace: list[str]
    constraint: str | None = None
