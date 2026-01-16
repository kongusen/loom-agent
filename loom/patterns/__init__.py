"""
Loom Patterns - 解决问题的模式

模式是一套配置和行为的组合，用于解决特定类型的问题。
作为通用框架，Loom 不预设具体 agent，而是提供方法论。
"""

from loom.patterns.analytical import AnalyticalPattern
from loom.patterns.base import Pattern
from loom.patterns.collaborative import CollaborativePattern
from loom.patterns.creative import CreativePattern
from loom.patterns.execution import ExecutionPattern
from loom.patterns.iterative import IterativePattern

# 模式注册表
PATTERNS = {
    "analytical": AnalyticalPattern(),
    "creative": CreativePattern(),
    "collaborative": CollaborativePattern(),
    "iterative": IterativePattern(),
    "execution": ExecutionPattern(),
}


def get_pattern(name: str) -> Pattern:
    """
    获取模式实例

    Args:
        name: 模式名称

    Returns:
        Pattern 实例

    Raises:
        ValueError: 如果模式不存在
    """
    if name not in PATTERNS:
        raise ValueError(
            f"Unknown pattern: {name}. " f"Available patterns: {', '.join(PATTERNS.keys())}"
        )
    return PATTERNS[name]


def list_patterns() -> list:
    """
    列出所有可用的模式

    Returns:
        模式名称列表
    """
    return list(PATTERNS.keys())


__all__ = [
    "Pattern",
    "AnalyticalPattern",
    "CreativePattern",
    "CollaborativePattern",
    "IterativePattern",
    "ExecutionPattern",
    "PATTERNS",
    "get_pattern",
    "list_patterns",
]
