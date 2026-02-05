"""
Loom Agent System - 核心智能体模块

本模块包含 Loom 的核心 Agent 实现：
- BaseNode: 所有节点的基础抽象
- Agent: 完整的四范式智能体（使用Mixin组合）
- AgentBuilder: 流畅的链式调用构建器

v0.5.1 重构：
- 拆分为多个Mixin模块，遵循单一职责原则
- 元工具定义合并到对应Mixin中
"""

from .base import BaseNode, NodeState
from .builder import AgentBuilder
from .core import Agent
from .delegator import create_delegate_task_tool
from .planner import create_plan_tool

__all__ = [
    # Core abstractions
    "BaseNode",
    "NodeState",
    "Agent",
    "AgentBuilder",
    # Meta-tools
    "create_delegate_task_tool",
    "create_plan_tool",
]
