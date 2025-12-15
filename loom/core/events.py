"""
Loom Events - 事件系统

定义框架内的事件类型，用于流式输出和观测
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime


class AgentEventType(str, Enum):
    """Agent 事件类型枚举"""

    # Agent 执行事件
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"

    # LLM 事件
    LLM_START = "llm_start"
    LLM_STREAM_CHUNK = "llm_stream_chunk"
    LLM_END = "llm_end"
    LLM_ERROR = "llm_error"

    # 工具事件
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"

    # Memory 事件
    MEMORY_ADD_START = "memory_add_start"
    MEMORY_ADD_END = "memory_add_end"
    MEMORY_LOAD_START = "memory_load_start"
    MEMORY_LOAD_END = "memory_load_end"
    MEMORY_CLEAR_START = "memory_clear_start"
    MEMORY_CLEAR_END = "memory_clear_end"

    # RAG 事件（v0.1.8 新增）
    MEMORY_RETRIEVE_START = "memory_retrieve_start"
    MEMORY_RETRIEVE_COMPLETE = "memory_retrieve_complete"
    MEMORY_VECTORIZE_START = "memory_vectorize_start"
    MEMORY_VECTORIZE_COMPLETE = "memory_vectorize_complete"

    # Ephemeral Memory 事件（v0.1.8 新增）
    EPHEMERAL_ADD = "ephemeral_add"
    EPHEMERAL_CLEAR = "ephemeral_clear"

    # 压缩事件
    COMPRESSION_START = "compression_start"
    COMPRESSION_END = "compression_end"

    # 通用事件
    INFO = "info"
    WARNING = "warning"
    DEBUG = "debug"


@dataclass(frozen=True)
class AgentEvent:
    """
    Agent 事件

    用于流式输出和观测性。

    Attributes:
        type: 事件类型
        data: 事件数据
        timestamp: 事件时间戳
        agent_name: Agent 名称（可选）
        metadata: 额外元数据
    """

    type: AgentEventType
    data: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    agent_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value if isinstance(self.type, Enum) else self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """用户友好的字符串表示"""
        agent_str = f" [{self.agent_name}]" if self.agent_name else ""
        return f"Event[{self.type.value}{agent_str}]"


# ============================================================================
# 便捷工厂函数
# ============================================================================


def create_agent_start_event(agent_name: str, message: str) -> AgentEvent:
    """创建 Agent 开始事件"""
    return AgentEvent(
        type=AgentEventType.AGENT_START,
        agent_name=agent_name,
        data={"message": message},
    )


def create_agent_end_event(agent_name: str, message: str) -> AgentEvent:
    """创建 Agent 结束事件"""
    return AgentEvent(
        type=AgentEventType.AGENT_END,
        agent_name=agent_name,
        data={"message": message},
    )


def create_llm_chunk_event(chunk: str, agent_name: Optional[str] = None) -> AgentEvent:
    """创建 LLM 流式输出事件"""
    return AgentEvent(
        type=AgentEventType.LLM_STREAM_CHUNK,
        agent_name=agent_name,
        data={"chunk": chunk},
    )


def create_tool_start_event(
    tool_name: str, args: Dict[str, Any], agent_name: Optional[str] = None
) -> AgentEvent:
    """创建工具开始事件"""
    return AgentEvent(
        type=AgentEventType.TOOL_START,
        agent_name=agent_name,
        data={"tool_name": tool_name, "args": args},
    )


def create_tool_end_event(
    tool_name: str, result: Any, agent_name: Optional[str] = None
) -> AgentEvent:
    """创建工具结束事件"""
    return AgentEvent(
        type=AgentEventType.TOOL_END,
        agent_name=agent_name,
        data={"tool_name": tool_name, "result": str(result)},
    )


def create_agent_error_event(
    agent_name: str, error: Exception, context: Optional[Dict[str, Any]] = None
) -> AgentEvent:
    """创建 Agent 错误事件"""
    return AgentEvent(
        type=AgentEventType.AGENT_ERROR,
        agent_name=agent_name,
        data={
            "error": str(error),
            "error_type": type(error).__name__,
            "context": context or {},
        },
    )


def create_llm_start_event(agent_name: str, data: Optional[Dict[str, Any]] = None) -> AgentEvent:
    """创建 LLM 开始事件"""
    return AgentEvent(
        type=AgentEventType.LLM_START,
        agent_name=agent_name,
        data=data or {},
    )


def create_llm_end_event(agent_name: str, data: Optional[Dict[str, Any]] = None) -> AgentEvent:
    """创建 LLM 结束事件"""
    return AgentEvent(
        type=AgentEventType.LLM_END,
        agent_name=agent_name,
        data=data or {},
    )


__all__ = [
    "AgentEventType",
    "AgentEvent",
    "create_agent_start_event",
    "create_agent_end_event",
    "create_agent_error_event",
    "create_llm_start_event",
    "create_llm_end_event",
    "create_llm_chunk_event",
    "create_tool_start_event",
    "create_tool_end_event",
]
