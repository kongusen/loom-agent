"""
Loom Agent System - 核心智能体模块

本模块包含 Loom 的核心 Agent 实现：
- BaseNode: 所有节点的基础抽象
- Agent: 完整的四范式智能体
- AgentBuilder: 流畅的链式调用构建器
- Meta-tools: 高级编排工具

根据目录结构重构：
- Agent 是 Loom 的核心执行单元
- orchestration/ 只保留编排模式（Workflow, Crew, Router, Pipeline）
"""

from .base import BaseNode, NodeState
from .core import Agent, AgentBuilder
from .meta_tools import create_delegate_task_tool, execute_delegate_task

__all__ = [
    # Core abstractions
    "BaseNode",
    "NodeState",
    "Agent",
    "AgentBuilder",
    # Meta-tools
    "create_delegate_task_tool",
    "execute_delegate_task",
]
