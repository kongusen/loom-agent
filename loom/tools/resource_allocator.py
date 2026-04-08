"""Effort 资源分配

根据 Q11 实验结果实现动态资源分配
"""

from dataclasses import dataclass
from typing import Literal

EffortLevel = Literal["low", "medium", "high"]

@dataclass
class ResourceAllocation:
    """资源分配配置"""
    timeout: int
    token_budget: int
    tool_depth: int

def allocate_resources(effort: EffortLevel) -> ResourceAllocation:
    """根据 effort hint 分配资源

    实验结果:
    - low: 21s, 914 tokens, 深度 2, 质量 0.80
    - medium: 40s, 2559 tokens, 深度 4, 质量 0.83
    - high: 96s, 7003 tokens, 深度 7, 质量 0.94
    """
    allocations = {
        "low": ResourceAllocation(timeout=30, token_budget=1000, tool_depth=2),
        "medium": ResourceAllocation(timeout=60, token_budget=3000, tool_depth=4),
        "high": ResourceAllocation(timeout=120, token_budget=8000, tool_depth=7)
    }
    return allocations[effort]
