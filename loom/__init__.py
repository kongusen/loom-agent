"""
Loom Agent Framework

公理驱动的多智能体框架，支持四范式工作模式：
- 反思 (Reflection)
- 工具使用 (Tool Use)
- 规划 (Planning)
- 协作 (Collaboration)
"""

# Core exceptions
from loom.exceptions import LoomError, TaskComplete

# Core Agent abstractions
from loom.agent import Agent, BaseNode

__all__ = [
    # Exceptions
    "LoomError",
    "TaskComplete",
    # Core
    "Agent",
    "BaseNode",
]
