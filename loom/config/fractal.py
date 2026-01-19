"""
Fractal Configuration - 分形编排配置

配置分形自相似结构的参数，支持递归任务分解和动态编排。

基于公理A3（分形自相似公理）：
配置分形增长、修剪和策略选择。

设计原则：
1. 可控增长 - 限制深度和节点数
2. 智能触发 - 基于复杂度自动增长
3. 性能优化 - 自动修剪低效节点
"""

from enum import Enum

from pydantic import Field

from loom.config.base import LoomBaseConfig


class GrowthTrigger(str, Enum):
    """
    增长触发条件

    定义何时触发分形增长。
    """

    COMPLEXITY = "complexity"  # 基于任务复杂度
    ALWAYS = "always"  # 总是评估增长
    MANUAL = "manual"  # 仅手动触发
    NEVER = "never"  # 禁用分形模式


class GrowthStrategy(str, Enum):
    """
    增长策略

    定义节点增长的方式。
    """

    DECOMPOSE = "decompose"  # 分解为顺序子任务
    SPECIALIZE = "specialize"  # 创建领域专家
    PARALLELIZE = "parallelize"  # 并行执行
    ITERATE = "iterate"  # 迭代优化


class FractalConfig(LoomBaseConfig):
    """
    分形配置

    配置分形编排的行为和限制。
    """

    enabled: bool = Field(
        False,
        description="启用分形模式",
    )

    # === 结构限制 ===

    max_depth: int = Field(
        3,
        ge=0,
        le=10,
        description="最大深度（0 = 仅根节点）",
    )

    max_children: int = Field(
        5,
        ge=1,
        le=20,
        description="每个节点的最大子节点数",
    )

    max_total_nodes: int = Field(
        20,
        ge=1,
        le=100,
        description="最大总节点数（防止爆炸性增长）",
    )

    # === 增长控制 ===

    growth_trigger: GrowthTrigger = Field(
        GrowthTrigger.COMPLEXITY,
        description="增长触发条件",
    )

    default_strategy: GrowthStrategy = Field(
        GrowthStrategy.DECOMPOSE,
        description="默认增长策略",
    )

    complexity_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="复杂度阈值（0-1），超过此值触发增长",
    )

    confidence_threshold: float = Field(
        0.6,
        ge=0.0,
        le=1.0,
        description="置信度阈值（0-1），低于此值触发分解",
    )

    # === 修剪设置 ===

    enable_auto_pruning: bool = Field(
        True,
        description="自动修剪低效节点",
    )

    pruning_threshold: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="修剪阈值（0-1），低于此值的节点被修剪",
    )

    min_tasks_before_pruning: int = Field(
        3,
        ge=1,
        description="修剪前的最小任务数",
    )

    # === 性能跟踪 ===

    track_metrics: bool = Field(
        True,
        description="跟踪节点性能指标",
    )

    persist_to_memory: bool = Field(
        True,
        description="将结构性能持久化到 L4 记忆",
    )
