"""
LLM Provider Interface
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Literal

from pydantic import BaseModel

from loom.protocol.interfaces import LLMProviderProtocol


class LLMResponse(BaseModel):
    """
    Standardized response from an LLM.
    """
    content: str
    tool_calls: list[dict[str, Any]] = []
    token_usage: dict[str, int] | None = None


class StreamChunk(BaseModel):
    """
    Structured chunk for streaming LLM output.

    Enables real-time injection of thoughts into the stream (System 2 → System 1).

    Event Types:
    - text: 文本内容增量
    - tool_call_start: 工具调用开始（包含 tool name）
    - tool_call_delta: 工具调用参数增量（可选）
    - tool_call_complete: 工具调用完成（包含完整参数）
    - thought_injection: 思考注入（System 2 → System 1）
    - error: 错误信息
    - done: 流结束（包含 token_usage）
    """
    type: Literal[
        "text",
        "tool_call_start",
        "tool_call_delta",
        "tool_call_complete",
        "thought_injection",
        "error",
        "done"
    ]
    content: str | dict
    metadata: dict[str, Any] = {}


class LLMProvider(LLMProviderProtocol, ABC):
    """
    Abstract Interface for LLM Backends (OpenAI, Anthropic, Local).
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None
    ) -> LLMResponse:
        """
        Generate a response for a given chat history.
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream the response as structured chunks.

        UPGRADED: Now returns StreamChunk instead of raw strings,
        enabling real-time thought injection and tool call support.
        """
        # Stub to indicate this is an async generator
        if False:
            yield  # type: ignore[unreachable]
        raise NotImplementedError
