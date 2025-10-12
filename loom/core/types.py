from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    role: str  # user | assistant | system | tool
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_call_id: Optional[str] = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    tool_call_id: str
    status: str  # success | error | warning
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamEvent:
    type: str  # text_delta | tool_calls_start | tool_result | agent_finish | error | aborted
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    result: Optional[ToolResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

