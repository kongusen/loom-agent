"""
Mock LLM Provider for Testing
"""

from collections.abc import AsyncGenerator
from typing import Any

from loom.llm.interface import LLMProvider, LLMResponse, StreamChunk


class MockLLMProvider(LLMProvider):
    """
    A Mock Provider that returns canned responses.
    Useful for unit testing and demos without API keys.

    UPGRADED: Now supports structured streaming with StreamChunk.
    """

    async def chat(
        self,
        messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]] | None = None,
        _config: dict[str, Any] | None = None,
    ) -> LLMResponse:
        last_msg = messages[-1]["content"].lower()

        # Simple keywords
        if "search" in last_msg:
            # Simulate Tool Call
            query = last_msg.replace("search", "").strip() or "fractal"
            return LLMResponse(
                content="",
                tool_calls=[
                    {"name": "search", "arguments": {"query": query}, "id": "call_mock_123"}
                ],
            )

        return LLMResponse(content=f"Mock response to: {last_msg}")

    async def stream_chat(
        self, messages: list[dict[str, Any]], _tools: list[dict[str, Any]] | None = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        UPGRADED: Now yields structured StreamChunk objects.
        Supports text, tool_call, thought_injection, and done events.
        """
        last_msg = messages[-1]["content"].lower()

        if "search" in last_msg or "calculate" in last_msg:
            # Simulate Tool Call in stream
            query = last_msg.replace("search", "").replace("calculate", "").strip() or "fractal"
            yield StreamChunk(
                type="tool_call_start",
                content={
                    "name": "mock-calculator" if "calculate" in last_msg else "search",
                    "arguments": {"query": query},
                    "id": "call_mock_stream_123",
                },
            )
            yield StreamChunk(type="done", content="")
            return

        # Simulate streaming text response
        words = ["Mock ", "stream ", "response."]
        for word in words:
            yield StreamChunk(type="text", content=word, metadata={"index": words.index(word)})

        # Signal stream completion
        yield StreamChunk(type="done", content="", metadata={"total_chunks": len(words)})
