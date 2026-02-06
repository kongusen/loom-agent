"""
Loom Framework - 统一对外API

基于六大公理系统的AI Agent框架。

核心导出：
- 协议层（A1）
- 事件层（A2）
- 分形层（A3）
- 记忆层（A4）
- 流式API
- 配置层
- 运行时
- 安全层
"""

# A1: 统一接口公理 - 协议层
# 配置层
from loom.config import ContextConfig
from loom.config.tool import ToolConfig

# A2: 事件主权公理 - 事件层
from loom.events import EventBus, SSEFormatter

# A3: 分形自相似公理 - 分形层
from loom.fractal import NodeContainer

# A4: 记忆层次公理 - 记忆层
from loom.memory import (
    MemoryManager,
    MemoryQuery,
    MemoryTier,
    MemoryType,
    MemoryUnit,
)
from loom.memory.compaction import CompactionConfig
from loom.memory.task_context import BudgetConfig
from loom.protocol import (
    AgentCapability,
    AgentCard,
    NodeProtocol,
    Task,
    TaskStatus,
)

# Runtime
from loom.runtime import Dispatcher, Interceptor, InterceptorChain
from loom.runtime.session_lane import SessionIsolationMode

# Security
from loom.security import BlacklistPolicy, ToolPolicy, WhitelistPolicy

# Stream API - 分形流式观测
from loom.api.stream_api import (
    FractalEvent,
    FractalStreamAPI,
    OutputStrategy,
    StreamAPI,
)

# Version API - 版本管理
from loom.api.version import (
    ChangeType,
    VersionAPI,
    VersionInfo,
    get_version,
    get_version_info,
)

__version__ = "0.5.3"

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
    "MemoryManager",
    "MemoryUnit",
    "MemoryTier",
    "MemoryType",
    "MemoryQuery",
    "ContextConfig",
    "ToolConfig",
    "CompactionConfig",
    "BudgetConfig",
    # Runtime
    "Dispatcher",
    "Interceptor",
    "InterceptorChain",
    "SessionIsolationMode",
    # Security
    "ToolPolicy",
    "WhitelistPolicy",
    "BlacklistPolicy",
    # Stream API
    "StreamAPI",
    "FractalStreamAPI",
    "FractalEvent",
    "OutputStrategy",
    # Version API
    "VersionAPI",
    "VersionInfo",
    "ChangeType",
    "get_version",
    "get_version_info",
]
