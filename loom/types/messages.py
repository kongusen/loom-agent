"""Message types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class SystemMessage:
    content: str
    role: str = "system"


@dataclass
class ContentPart:
    type: str = "text"  # "text" | "image"
    text: str | None = None
    image_url: str | None = None


@dataclass
class UserMessage:
    content: str | list[ContentPart] = ""
    role: str = "user"


@dataclass
class AssistantMessage:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    role: str = "assistant"


@dataclass
class ToolMessage:
    content: str
    tool_call_id: str
    role: str = "tool"


Message = SystemMessage | UserMessage | AssistantMessage | ToolMessage
