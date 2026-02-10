"""
Context Module - 上下文构建层

基于 Anthropic Context Engineering 思想的上下文管理系统。

核心原则：
1. Token-First Design: 所有操作以 token 为单位
2. Quality over Quantity: 质量优于数量
3. Just-in-Time Context: 按需加载
4. Context Compaction: 智能压缩
"""

from loom.context.block import ContextBlock
from loom.context.budget import (
    BudgetAllocation,
    BudgetManager,
    TokenBudget,
)
from loom.context.collector import ContextCollector
from loom.context.compactor import CompactionLevel, ContextCompactor
from loom.context.orchestrator import ContextOrchestrator
from loom.context.source import ContextSource

__all__ = [
    # 核心数据结构
    "ContextBlock",
    "TokenBudget",
    "BudgetAllocation",
    # 管理器
    "BudgetManager",
    "ContextCollector",
    "ContextCompactor",
    "CompactionLevel",
    "ContextOrchestrator",
    # 接口
    "ContextSource",
]
