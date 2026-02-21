"""
A2: 事件主权公理 (Event Sovereignty Axiom)

公理陈述：∀communication ∈ System: communication = Task

本模块实现基于Task模型的事件系统，支持多种传输层。

导出内容：
- EventBus: 事件总线（任务路由和分发）
- TaskAction, MemoryAction, AgentAction: 类型安全的动作枚举
- TaskHandler, MemoryHandler, AgentHandler: 处理器协议
- SSEFormatter: SSE格式化工具（SSE消息格式化）
- OutputCollector, OutputStrategy, SSEEvent: 输出收集器（多Agent并行SSE支持）
- Transport: 传输层抽象接口
- MemoryTransport: 内存传输层（单机、测试）
- NATSTransport: NATS传输层（分布式、生产）- 需要安装nats-py
"""

from loom.events.actions import AgentAction, KnowledgeAction, MemoryAction, TaskAction
from loom.events.context_controller import ContextController
from loom.events.event_bus import EventBus
from loom.events.handlers import AgentHandler, MemoryHandler, TaskHandler
from loom.events.memory_transport import MemoryTransport
from loom.events.output_collector import OutputCollector, OutputStrategy, SSEEvent
from loom.events.session import Session, SessionStatus
from loom.events.sse_formatter import SSEFormatter
from loom.events.transport import Transport

# NATSTransport是可选的，需要安装nats-py
try:
    from loom.events.nats_transport import NATSTransport

    _NATS_AVAILABLE = True
except ImportError:
    NATSTransport = None  # type: ignore
    _NATS_AVAILABLE = False

__all__ = [
    "EventBus",
    "ContextController",
    "Session",
    "SessionStatus",
    "TaskAction",
    "MemoryAction",
    "AgentAction",
    "KnowledgeAction",
    "TaskHandler",
    "MemoryHandler",
    "AgentHandler",
    "SSEFormatter",
    "OutputCollector",
    "OutputStrategy",
    "SSEEvent",
    "Transport",
    "MemoryTransport",
]

# 只有在nats-py可用时才导出NATSTransport
if _NATS_AVAILABLE:
    __all__.append("NATSTransport")
