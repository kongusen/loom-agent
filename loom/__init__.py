"""
Loom Agent Framework

公理驱动的多智能体框架，支持四范式工作模式：
- 反思 (Reflection)
- 工具使用 (Tool Use)
- 规划 (Planning)
- 协作 (Collaboration)
"""

from importlib.metadata import version as _version

__version__ = _version("loom-agent")

# Core Agent abstractions
from loom.agent import Agent, AgentBuilder, BaseNode
from loom.agent.factory import AgentFactory
from loom.config.context import ContextConfig
from loom.config.memory import MemoryConfig

# Config (渐进式披露)
from loom.config.tool import ToolConfig

# Events
from loom.events.event_bus import EventBus
from loom.memory.shared_pool import SharedMemoryPool

# Exceptions
from loom.exceptions import (
    ConfigurationError,
    ContextBuildError,
    DelegationError,
    LLMProviderError,
    LoomError,
    MaxIterationsExceeded,
    MemoryBudgetExceeded,
    PermissionDenied,
    TaskComplete,
    ToolExecutionError,
    ToolNotFoundError,
)

# Observability
from loom.observability import (
    ConsoleSpanExporter,
    LoomMetrics,
    LoomTracer,
    OTLPMetricsExporter,
    OTLPSpanExporter,
    setup_otlp,
)

# Runtime
from loom.runtime import Task, TaskStatus

__all__ = [
    "__version__",
    # Core
    "Agent",
    "AgentBuilder",
    "AgentFactory",
    "BaseNode",
    # Runtime
    "Task",
    "TaskStatus",
    "EventBus",
    # Exceptions
    "LoomError",
    "TaskComplete",
    "PermissionDenied",
    "ToolExecutionError",
    "ToolNotFoundError",
    "MemoryBudgetExceeded",
    "ContextBuildError",
    "MaxIterationsExceeded",
    "DelegationError",
    "LLMProviderError",
    "ConfigurationError",
    # Observability
    "LoomTracer",
    "LoomMetrics",
    "OTLPSpanExporter",
    "OTLPMetricsExporter",
    "ConsoleSpanExporter",
    "setup_otlp",
    # Memory
    "SharedMemoryPool",
    # Config
    "ToolConfig",
    "ContextConfig",
    "MemoryConfig",
]
