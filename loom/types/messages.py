"""Message types for Agent communication"""

from dataclasses import dataclass, field
from typing import Any, Literal

from .content import MessageContent


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
    """Base message type with multimodal support

    Content can be:
    - str: Simple text message
    - list[ContentBlock]: Multimodal content with text, images, documents

    Examples:
        # Text only
        Message(role="user", content="Hello")

        # With image
        Message(role="user", content=[
            TextBlock(text="What's in this image?"),
            ImageBlock(source={"type": "url", "url": "https://..."})
        ])
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: MessageContent = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None
