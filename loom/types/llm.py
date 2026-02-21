"""LLM provider types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Literal, Protocol, runtime_checkable

from .messages import Message, AssistantMessage, ToolCall
from .tools import ToolDefinition
from .events import TokenUsage

FinishReason = Literal["stop", "tool_calls", "length"]


@dataclass
class CompletionParams:
    messages: list[Message]
    tools: list[ToolDefinition] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    stop: list[str] | None = None


@dataclass
class CompletionResult:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: FinishReason = "stop"


@dataclass
class StreamOptions:
    signal: Any | None = None


@dataclass
class StreamChunk:
    text: str | None = None
    tool_call: ToolCall | None = None
    finish_reason: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, params: CompletionParams) -> CompletionResult: ...
    async def stream(self, params: CompletionParams) -> AsyncGenerator[StreamChunk, None]: ...
