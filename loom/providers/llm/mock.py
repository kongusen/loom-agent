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
        # 默认行为（基于关键词）
        provider = MockLLMProvider()
        response = await provider.chat(messages=[...])

        # 预设响应序列（用于测试）
        provider = MockLLMProvider(responses=[
            {"type": "text", "content": "思考中..."},
            {"type": "tool_call", "name": "calculator", "arguments": {"a": 2, "b": 3}},
            {"type": "text", "content": "结果是5"},
            {"type": "tool_call", "name": "done", "arguments": {"message": "完成"}},
        ])
    """

    def __init__(self, responses: list[dict[str, Any]] | None = None):
        """
        初始化MockLLMProvider

        Args:
            responses: 预设的响应序列。如果为None，使用默认的关键词匹配行为。
                每个响应是一个字典：
                - {"type": "text", "content": "文本内容"}
                - {"type": "tool_call", "name": "工具名", "arguments": {...}}
        """
        self.responses = responses
        self.call_count = 0  # 跟踪调用次数（用于多轮对话）

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> LLMResponse:
        """非流式调用 - 返回预设响应"""
        # 如果有预设响应，使用预设响应序列
        if self.responses is not None and self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1

            if response["type"] == "text":
                return LLMResponse(content=response["content"])
            elif response["type"] == "tool_call":
                return LLMResponse(
                    content="",
                    tool_calls=[
                        {
                            "name": response["name"],
                            "arguments": response["arguments"],
                            "id": f"call_mock_{self.call_count}",
                        }
                    ],
                )

        # 默认行为（关键词匹配）
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

        # 如果有预设响应，使用预设响应序列
        if self.responses is not None:
            # 只处理当前 call_count 对应的响应
            if self.call_count < len(self.responses):
                response = self.responses[self.call_count]
                self.call_count += 1

                if response["type"] == "text":
                    yield StreamChunk(type="text", content=response["content"], metadata={})
                elif response["type"] == "tool_call":
                    yield StreamChunk(
                        type="tool_call_complete",
                        content={
                            "name": response["name"],
                            "arguments": response["arguments"],
                            "id": f"call_mock_{self.call_count}",
                        },
                        metadata={},
                    )
            return

        # 否则使用默认的关键词匹配逻辑
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
