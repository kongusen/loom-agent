"""
投影配置和模式定义

定义了不同场景下的投影策略配置。
"""

from dataclasses import dataclass
from enum import Enum


class ProjectionMode(Enum):
    """投影模式枚举

    定义了5种不同的投影模式，适用于不同的任务场景。
    """

    MINIMAL = "minimal"  # 工具调用、简单计算
    STANDARD = "standard"  # 默认平衡模式
    CONTEXTUAL = "contextual"  # 需要理解对话上下文
    ANALYTICAL = "analytical"  # 需要深度知识检索
    DEBUG = "debug"  # 错误修复、重试


@dataclass
class ProjectionConfig:
    """投影配置

    定义了投影过程中的各项参数配置。

    Attributes:
        mode: 投影模式
        vip_ratio: VIP内容（plan, recent turns, errors）占总预算的比例
        l4_ratio: L4 facts 占总预算的比例
        max_l4_facts: 最大投影的 L4 facts 数量
        importance_weight: 重要性权重（用于混合评分）
        relevance_weight: 相关性权重（用于混合评分）
    """

    mode: ProjectionMode
    vip_ratio: float
    l4_ratio: float
    max_l4_facts: int
    importance_weight: float = 0.3
    relevance_weight: float = 0.7

    @classmethod
    def from_mode(cls, mode: ProjectionMode) -> "ProjectionConfig":
        """根据模式创建配置

        Args:
            mode: 投影模式

        Returns:
            对应模式的配置实例
        """
        configs = {
            ProjectionMode.MINIMAL: cls(
                mode=mode,
                vip_ratio=0.1,
                l4_ratio=0.8,
                max_l4_facts=2,
                importance_weight=0.5,
                relevance_weight=0.5,
            ),
            ProjectionMode.STANDARD: cls(
                mode=mode,
                vip_ratio=0.3,
                l4_ratio=0.6,
                max_l4_facts=8,
                importance_weight=0.3,
                relevance_weight=0.7,
            ),
            ProjectionMode.CONTEXTUAL: cls(
                mode=mode,
                vip_ratio=0.5,
                l4_ratio=0.4,
                max_l4_facts=5,
                importance_weight=0.2,
                relevance_weight=0.8,
            ),
            ProjectionMode.ANALYTICAL: cls(
                mode=mode,
                vip_ratio=0.2,
                l4_ratio=0.7,
                max_l4_facts=15,
                importance_weight=0.3,
                relevance_weight=0.7,
            ),
            ProjectionMode.DEBUG: cls(
                mode=mode,
                vip_ratio=0.6,
                l4_ratio=0.3,
                max_l4_facts=5,
                importance_weight=0.1,
                relevance_weight=0.9,
            ),
        }
        return configs[mode]
