"""
Loom Framework - 统一对外API

基于六大公理系统的AI Agent框架。

核心导出：
- 协议层（A1）
- 事件层（A2）
- 分形层（A3）
- 记忆层（A4）
- 编排层（A5）
- 范式层（A6）
- 运行时
"""

# A1: 统一接口公理
# FastAPI-style API - LoomApp (类型安全、Pydantic 验证)
from loom.api.app import LoomApp
from loom.api.models import AgentConfig

# A2: 事件主权公理
from loom.events import EventBus, SSEFormatter

# A3: 分形自相似公理
from loom.fractal import NodeContainer

# A4: 记忆层次公理
from loom.memory import (
    LoomMemory,
    MemoryQuery,
    MemoryTier,
    MemoryType,
    MemoryUnit,
)

# A5: 认知调度公理
from loom.orchestration import CrewOrchestrator, RouterOrchestrator

# A6: 四范式工作公理 - 现已集成到 Agent 基础能力中
from loom.protocol import (
    AgentCapability,
    AgentCard,
    NodeProtocol,
    Task,
    TaskStatus,
)

# Runtime
from loom.runtime import Dispatcher, Interceptor, InterceptorChain

__version__ = "0.4.0-alpha"

__all__ = [
    # Protocol
    "NodeProtocol",
    "Task",
    "TaskStatus",
    "AgentCard",
    "AgentCapability",
    # Events
    "EventBus",
    "SSEFormatter",
    # Fractal
    "NodeContainer",
    # Memory
    "LoomMemory",
    "MemoryUnit",
    "MemoryTier",
    "MemoryType",
    "MemoryQuery",
    # Orchestration
    "RouterOrchestrator",
    "CrewOrchestrator",
    # Runtime
    "Dispatcher",
    "Interceptor",
    "InterceptorChain",
    # API - FastAPI-style
    "LoomApp",
    "AgentConfig",
]
