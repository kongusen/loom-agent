"""
Memory Configuration - 记忆系统配置

配置四层记忆系统（L1-L4）的参数和策略。

基于公理A4（记忆层次公理）：
配置记忆的容量、保留时间和管理策略。

设计原则：
1. 分层配置 - 每层独立配置
2. 策略灵活 - 支持多种记忆策略
3. 合理默认 - 提供开箱即用的默认值
"""

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import Field

from loom.config.base import LoomBaseConfig

if TYPE_CHECKING:
    from loom.config.knowledge import KnowledgeBaseProvider


class MemoryStrategyType(str, Enum):
    """
    记忆策略类型

    定义记忆项的提升和压缩策略。
    """

    SIMPLE = "simple"  # 基于访问次数的简单策略
    TIME_BASED = "time_based"  # 基于时间的策略
    IMPORTANCE_BASED = "importance_based"  # 基于重要性的策略


class MemoryLayerConfig(LoomBaseConfig):
    """
    单层记忆配置

    配置单个记忆层的参数。
    """

    capacity: int = Field(
        10,
        ge=1,
        le=10000,
        description="层容量（最大记忆项数量）",
    )

    retention_hours: int | None = Field(
        None,
        ge=0,
        description="保留时间（小时），None 表示永久保留",
    )

    auto_compress: bool = Field(
        True,
        description="是否自动压缩",
    )

    promote_threshold: int = Field(
        3,
        ge=0,
        description="提升阈值（访问次数），0 表示不提升",
    )


class MemoryConfig(LoomBaseConfig):
    """
    记忆系统配置

    配置完整的四层记忆系统。

    层级说明：
    - L1: 工作记忆（Working Memory）- 当前对话上下文
    - L2: 会话记忆（Session Memory）- 当前会话历史
    - L3: 情节记忆（Episodic Memory）- 跨会话的重要事件
    - L4: 语义记忆（Semantic Memory）- 长期知识和事实
    """

    strategy: MemoryStrategyType = Field(
        MemoryStrategyType.SIMPLE,
        description="记忆管理策略",
    )

    l1: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(
            capacity=10,
            retention_hours=1,
            auto_compress=True,
            promote_threshold=3,
        ),
        description="L1 工作记忆配置",
    )

    l2: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(
            capacity=50,
            retention_hours=24,
            auto_compress=True,
            promote_threshold=5,
        ),
        description="L2 会话记忆配置",
    )

    l3: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(
            capacity=200,
            retention_hours=168,  # 7 days
            auto_compress=True,
            promote_threshold=10,
        ),
        description="L3 情节记忆配置",
    )

    l4: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(
            capacity=1000,
            retention_hours=None,  # 永久保留
            auto_compress=False,
            promote_threshold=0,  # L4 不再提升
        ),
        description="L4 语义记忆配置",
    )

    enable_auto_migration: bool = Field(
        True,
        description="启用自动迁移（根据策略自动提升记忆项）",
    )

    enable_compression: bool = Field(
        True,
        description="启用压缩（自动压缩满层）",
    )

    knowledge_base: "KnowledgeBaseProvider | None" = Field(
        None,
        description="外部知识库提供者（可选）",
    )
