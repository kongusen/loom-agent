"""Message types for Agent communication"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

# Import content types for multimodal support
if TYPE_CHECKING:
    from .content import ContentBlock, MessageContent
else:
    # Runtime fallback if content.py doesn't exist yet
    try:
        from .content import ContentBlock, MessageContent
    except ImportError:
        ContentBlock = None  # type: ignore
        MessageContent = str  # type: ignore


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
    - str: Simple text message (backward compatible)
    - list[ContentBlock]: Multimodal content with text, images, documents

    Examples:
        # Text only (backward compatible)
        Message(role="user", content="Hello")

        # With image
        Message(role="user", content=[
            TextBlock(text="What's in this image?"),
            ImageBlock(source={"type": "url", "url": "https://..."})
        ])
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list = ""  # MessageContent type, but using Union[str, list] for compatibility
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None
