# loom/core/message.py

from typing import Optional, Union, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4

# ============ Content Types ============

class TextContent(BaseModel):
    """Pure text content."""
    type: Literal["text"] = "text"
    text: str


class ImageContent(BaseModel):
    """Image content (supports URL and base64)."""
    type: Literal["image_url"] = "image_url"
    image_url: Union[str, Dict[str, str]]  # URL or {"url": "...", "detail": "high"}


class AudioContent(BaseModel):
    """Audio content."""
    type: Literal["audio_url"] = "audio_url"
    audio_url: str


class VideoContent(BaseModel):
    """Video content."""
    type: Literal["video_url"] = "video_url"
    video_url: str


ContentPart = Union[TextContent, ImageContent, AudioContent, VideoContent]


# ============ Tool Call Types ============

class FunctionCall(BaseModel):
    """Function call detail."""
    name: str
    arguments: str  # JSON string (compatible with OpenAI)


class ToolCall(BaseModel):
    """Tool call (OpenAI format)."""
    id: str = Field(default_factory=lambda: f"call_{uuid4().hex[:24]}")
    type: Literal["function"] = "function"
    function: FunctionCall


# ============ Message Types ============

class BaseMessage(BaseModel):
    """
    Base class for all messages.

    Design Philosophy:
    - Mutable by default (removed frozen=True from v0.2.0)
    - Pydantic v2 for validation
    - OpenAI compatible but extensible
    """

    role: str  # system, user, assistant, tool
    content: Union[str, List[ContentPart], None] = None

    # Metadata
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # OpenAI compatibility
    name: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)

    def get_text_content(self) -> str:
        """Extract pure text content."""
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, list):
            texts = [
                part.text for part in self.content
                if isinstance(part, TextContent)
            ]
            return "\n".join(texts)
        return ""

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI API format."""
        msg = {"role": self.role}

        if self.content is not None:
            if isinstance(self.content, str):
                msg["content"] = self.content
            elif isinstance(self.content, list):
                msg["content"] = [part.model_dump() for part in self.content]

        if self.name:
            msg["name"] = self.name

        return msg


class SystemMessage(BaseMessage):
    """System message."""
    role: Literal["system"] = "system"
    content: str  # System prompt must be a string

    def __init__(self, content: str, **kwargs):
        super().__init__(role="system", content=content, **kwargs)


class UserMessage(BaseMessage):
    """User message (supports multi-modal)."""
    role: Literal["user"] = "user"

    # Quick access helpers for multi-modal (not stored directly in DB, parsed into content)
    # These fields are primarily for initialization convenience
    images: Optional[List[str]] = None
    audio: Optional[str] = None
    video: Optional[str] = None

    def __init__(self, content: str, images: Optional[List[str]] = None, **kwargs):
        # Automatically construct multi-modal content if images are provided
        if images:
            content_parts: List[ContentPart] = [TextContent(text=content)]
            content_parts.extend([
                ImageContent(image_url=img) for img in images
            ])
            super().__init__(role="user", content=content_parts, images=images, **kwargs)
        else:
            super().__init__(role="user", content=content, **kwargs)


class AssistantMessage(BaseMessage):
    """Assistant message (supports tool calls)."""
    role: Literal["assistant"] = "assistant"
    tool_calls: Optional[List[ToolCall]] = None

    def __init__(self, content: Optional[str] = None, tool_calls: Optional[List[ToolCall]] = None, **kwargs):
        super().__init__(role="assistant", content=content, tool_calls=tool_calls, **kwargs)

    def to_openai_format(self) -> Dict[str, Any]:
        msg = super().to_openai_format()
        if self.tool_calls:
            msg["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
        return msg


class ToolMessage(BaseMessage):
    """Tool execution result message."""
    role: Literal["tool"] = "tool"
    tool_call_id: str

    def __init__(self, tool_call_id: str, content: str, **kwargs):
        super().__init__(role="tool", content=content, tool_call_id=tool_call_id, **kwargs)

    def to_openai_format(self) -> Dict[str, Any]:
        msg = super().to_openai_format()
        msg["tool_call_id"] = self.tool_call_id
        return msg


# Type Aliases
Message = Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage]


# ============ Helper Functions ============

def create_message(
    role: str,
    content: Optional[str] = None,
    **kwargs
) -> Message:
    """
    Factory function: create corresponding Message based on role.

    Example:
        msg = create_message("user", "Hello")
        msg = create_message("assistant", tool_calls=[...])
    """
    if role == "system":
        return SystemMessage(content=content or "", **kwargs)
    elif role == "user":
        return UserMessage(content=content or "", **kwargs)
    elif role == "assistant":
        return AssistantMessage(content=content, **kwargs)
    elif role == "tool":
        if "tool_call_id" not in kwargs:
             raise ValueError("tool_call_id is required for ToolMessage")
        return ToolMessage(content=content or "", **kwargs)
    else:
        raise ValueError(f"Unknown role: {role}")


def messages_to_openai_format(messages: List[Message]) -> List[Dict[str, Any]]:
    """Batch convert to OpenAI format."""
    return [msg.to_openai_format() for msg in messages]

