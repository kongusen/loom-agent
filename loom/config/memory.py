"""
Memory Configuration - 记忆系统配置

配置四层记忆系统（L1-L4）的参数和策略。

基于公理A4（记忆层次公理）：
配置记忆的容量、保留时间和管理策略。

设计原则：
1. Token-First Design - 所有容量以 token 为单位
2. Quality over Quantity - 质量优于数量
3. Just-in-Time Context - 按需加载
4. Context Compaction - 智能压缩
"""

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import Field

from loom.config.base import LoomBaseConfig

if TYPE_CHECKING:
    from loom.providers.knowledge.base import KnowledgeBaseProvider


class MemoryStrategyType(StrEnum):
    """
    记忆策略类型

    定义记忆项的提升和压缩策略。
    """

    SIMPLE = "simple"  # 基于访问次数的简单策略
    TIME_BASED = "time_based"  # 基于时间的策略
    IMPORTANCE_BASED = "importance_based"  # 基于重要性的策略


class MemoryLayerConfig(LoomBaseConfig):
    """
    单层记忆配置（Token-First Design）

    配置单个记忆层的参数，所有容量以 token 为单位。
    """

    token_budget: int = Field(
        4000,
        ge=100,
        le=1000000,
        description="层 token 预算（最大 token 数）",
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

    compress_threshold: float = Field(
        0.9,
        ge=0.5,
        le=1.0,
        description="压缩触发阈值（使用率）",
    )

    importance_threshold: float = Field(
        0.6,
        ge=0.0,
        le=1.0,
        description="重要性阈值（低于此值的内容优先压缩）",
    )


class MemoryConfig(LoomBaseConfig):
    """
    记忆系统配置（Token-First Design）

    配置完整的四层记忆系统，所有容量以 token 为单位。

    层级说明：
    - L1: 工作记忆（Working Memory）- 当前对话上下文，高频访问
    - L2: 会话记忆（Session Memory）- 当前会话重要内容
    - L3: 情节记忆（Episodic Memory）- 会话摘要
    - L4: 语义记忆（Semantic Memory）- 跨会话向量记忆
    """

    strategy: MemoryStrategyType = Field(
        MemoryStrategyType.IMPORTANCE_BASED,
        description="记忆管理策略",
    )

    l1: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(
            token_budget=8000,
            retention_hours=1,
            auto_compress=True,
            compress_threshold=0.9,
            importance_threshold=0.5,
        ),
        description="L1 工作记忆配置",
    )

    l2: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(
            token_budget=16000,
            retention_hours=24,
            auto_compress=True,
            compress_threshold=0.85,
            importance_threshold=0.6,
        ),
        description="L2 会话记忆配置",
    )

    l3: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(
            token_budget=32000,
            retention_hours=168,  # 7 days
            auto_compress=True,
            compress_threshold=0.9,
            importance_threshold=0.4,
        ),
        description="L3 情节记忆配置",
    )

    l4: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(
            token_budget=100000,
            retention_hours=None,  # 永久保留
            auto_compress=False,
            compress_threshold=0.95,
            importance_threshold=0.3,
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
