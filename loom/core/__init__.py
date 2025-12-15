"""
Loom Core - 核心组件

核心模块：
- Message: 统一消息
- BaseAgent: Agent 协议
- AgentExecutor: 执行引擎
- ContextManager: Context 管理
- ContextAssembler: 智能上下文组装器 (v0.1.7)
- EnhancedContextManager: 增强的 Context 管理 (v0.1.7)
- Events: 事件系统
- Errors: 错误处理
"""

from loom.core.message import Message
from loom.core.base_agent import (
    BaseAgent,
    create_agent,
    is_agent,
    validate_agent,
)
from loom.core.executor import AgentExecutor
from loom.core.context import ContextManager, create_context_manager
from loom.core.context_assembler import (
    ContextAssembler,
    EnhancedContextManager,
    ComponentPriority,
    ContextComponent,
)
from loom.core.events import AgentEvent, AgentEventType
from loom.core.errors import (
    LoomError,
    AgentError,
    ExecutionError,
    ToolError,
    RecursionError,
    ContextError,
    CompressionError,
    MemoryError,
    LLMError,
    ValidationError,
    ConfigurationError,
)

__all__ = [
    # Message
    "Message",
    # Agent
    "BaseAgent",
    "create_agent",
    "is_agent",
    "validate_agent",
    # Executor
    "AgentExecutor",
    # Context
    "ContextManager",
    "create_context_manager",
    # Context Assembler (v0.1.7)
    "ContextAssembler",
    "EnhancedContextManager",
    "ComponentPriority",
    "ContextComponent",
    # Events
    "AgentEvent",
    "AgentEventType",
    # Errors
    "LoomError",
    "AgentError",
    "ExecutionError",
    "ToolError",
    "RecursionError",
    "ContextError",
    "CompressionError",
    "MemoryError",
    "LLMError",
    "ValidationError",
    "ConfigurationError",
]
