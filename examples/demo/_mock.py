"""共享 Mock 组件 — 让所有 demo 无需真实 API Key 即可运行。"""

from __future__ import annotations
from typing import AsyncGenerator

from loom.types import (
    CompletionParams, CompletionResult, StreamChunk, TokenUsage, ToolCall,
)


class MockProvider:
    """Mock LLM — 根据输入关键词返回预设回复，支持 tool_calls。"""

    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses or {}
        self._default = "这是 MockProvider 的回复。"
        self._call_count = 0

    async def complete(self, params: CompletionParams) -> CompletionResult:
        self._call_count += 1
        last = next((m for m in reversed(params.messages) if m.role == "user"), None)
        text = last.content if last else ""

        # 检查是否有工具可用且输入匹配
        for tool in params.tools:
            if tool.name in text.lower():
                return CompletionResult(
                    content="",
                    tool_calls=[ToolCall(id=f"call_{self._call_count}", name=tool.name, arguments="{}")],
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    finish_reason="tool_calls",
                )

        # 关键词匹配回复
        for key, resp in self._responses.items():
            if key in text:
                return CompletionResult(
                    content=resp,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
                )

        return CompletionResult(
            content=self._default,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        )

    async def stream(self, params: CompletionParams) -> AsyncGenerator[StreamChunk, None]:
        result = await self.complete(params)
        if result.tool_calls:
            for tc in result.tool_calls:
                yield StreamChunk(tool_call=tc)
        else:
            for word in result.content.split():
                yield StreamChunk(text=word + " ")
        yield StreamChunk(finish_reason="stop")


class MockEmbedder:
    """Mock 向量嵌入 — 基于字符哈希生成固定维度向量。"""

    def __init__(self, dim: int = 8):
        self._dim = dim

    async def embed(self, text: str) -> list[float]:
        h = hash(text)
        return [(h >> i & 0xFF) / 255.0 for i in range(self._dim)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]
