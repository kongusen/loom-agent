"""
Mock LLM Provider for Testing

基于第一性原理简化：
1. 直接实现 LLMProvider 接口
2. 返回预设响应，用于测试
3. 支持简单的工具调用模拟
"""

from collections.abc import AsyncGenerator
from typing import Any

from loom.providers.llm.interface import LLMProvider, LLMResponse, StreamChunk


class MockLLMProvider(LLMProvider):
    """
    Mock Provider - 返回预设响应

    用于单元测试和演示，无需 API key。

    使用方式：
        provider = MockLLMProvider()
        response = await provider.chat(messages=[...])
    """

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> LLMResponse:
        """非流式调用 - 返回预设响应"""
        last_msg = messages[-1]["content"].lower()

        # 模拟工具调用
        if "search" in last_msg:
            query = last_msg.replace("search", "").strip() or "fractal"
            return LLMResponse(
                content="",
                tool_calls=[
                    {"name": "search", "arguments": {"query": query}, "id": "call_mock_123"}
                ],
            )

        return LLMResponse(content=f"Mock response to: {last_msg}")

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式调用 - 返回预设的流式响应"""
        last_msg = messages[-1]["content"].lower()

        # 模拟工具调用
        if "search" in last_msg or "calculate" in last_msg:
            query = last_msg.replace("search", "").replace("calculate", "").strip() or "fractal"
            tool_name = "mock-calculator" if "calculate" in last_msg else "search"

            yield StreamChunk(
                type="tool_call_start",
                content={"name": tool_name, "id": "call_mock_stream_123", "index": 0},
                metadata={},
            )

            yield StreamChunk(
                type="tool_call_complete",
                content={
                    "name": tool_name,
                    "arguments": {"query": query},
                    "id": "call_mock_stream_123",
                },
                metadata={"index": 0},
            )

            yield StreamChunk(type="done", content="", metadata={})
            return

        # 模拟流式文本响应
        words = ["Mock ", "stream ", "response."]
        for i, word in enumerate(words):
            yield StreamChunk(type="text", content=word, metadata={"index": i})

        # 完成信号
        yield StreamChunk(type="done", content="", metadata={"total_chunks": len(words)})
