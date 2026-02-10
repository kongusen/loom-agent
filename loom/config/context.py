"""
Context Configuration - 上下文流动配置

聚合与上下文流动相关的配置：
- 记忆系统（MemoryConfig）
- 上下文预算（BudgetConfig）
- 记忆压缩（CompactionConfig）
- Session 隔离（SessionIsolationMode）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import Field, field_validator

from loom.config.base import LoomBaseConfig
from loom.config.memory import MemoryConfig
from loom.runtime.session_lane import SessionIsolationMode


@dataclass
class BudgetConfig:
    """
    上下文预算配置

    用于配置各层的预算分配比例。
    """

    l1_ratio: float = 0.25
    l2_ratio: float = 0.20
    l3_l4_ratio: float = 0.30
    rag_ratio: float = 0.15
    inherited_ratio: float = 0.10

if TYPE_CHECKING:
    from loom.memory.compaction import CompactionConfig


class ContextConfig(LoomBaseConfig):
    """
    上下文配置（聚合）

    设计目标：
    - 对外 API 统一入口
    - 便于用户整体调整上下文流动策略
    """

    memory: MemoryConfig | None = Field(
        default=None,
        description="记忆系统配置",
    )
    budget: BudgetConfig | None = Field(
        default=None,
        description="上下文预算配置",
    )
    compaction: CompactionConfig | None = Field(
        default=None,
        description="记忆压缩配置",
    )
    session_isolation: SessionIsolationMode = Field(
        default=SessionIsolationMode.STRICT,
        description="Session 隔离模式",
    )

    @field_validator("memory", mode="before")
    @classmethod
    def _coerce_memory(cls, value: Any) -> Any:
        if value is None or isinstance(value, MemoryConfig):
            return value
        if isinstance(value, dict):
            return MemoryConfig(**value)
        raise TypeError("memory must be MemoryConfig or dict")

    @field_validator("budget", mode="before")
    @classmethod
    def _coerce_budget(cls, value: Any) -> Any:
        if value is None or isinstance(value, BudgetConfig):
            return value
        if isinstance(value, dict):
            return BudgetConfig(**value)
        raise TypeError("budget must be BudgetConfig or dict")

    @field_validator("compaction", mode="before")
    @classmethod
    def _coerce_compaction(cls, value: Any) -> Any:
        if value is None:
            return value
        from loom.memory.compaction import CompactionConfig

        if isinstance(value, CompactionConfig):
            return value
        if isinstance(value, dict):
            return CompactionConfig(**value)
        raise TypeError("compaction must be CompactionConfig or dict")

    @field_validator("session_isolation", mode="before")
    @classmethod
    def _coerce_session_isolation(cls, value: Any) -> Any:
        if isinstance(value, SessionIsolationMode):
            return value
        if isinstance(value, str):
            return SessionIsolationMode(value)
        raise TypeError("session_isolation must be SessionIsolationMode or str")
