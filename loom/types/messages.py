"""Message types for Agent communication"""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolCall:
    """Tool invocation request"""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Tool execution result"""
    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class Message:
    """Base message type"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None
