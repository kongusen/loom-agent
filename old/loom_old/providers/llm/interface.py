"""
LLM Provider Interface - 简化版

基于第一性原理简化：
1. 移除thought_injection（过度设计）
2. 移除tool_call_delta（简化为start+complete）
3. 保留5种核心事件类型
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Literal

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """
    标准化的LLM响应

    Attributes:
        content: 文本内容
        tool_calls: 工具调用列表
        token_usage: token使用统计
    """

    content: str
    tool_calls: list[dict[str, Any]] = []
    token_usage: dict[str, int] | None = None


class StreamChunk(BaseModel):
    """
    流式输出的结构化块

    简化的事件类型（5种）：
    - text: 文本内容增量
    - tool_call_start: 工具调用开始
    - tool_call_complete: 工具调用完成
    - error: 错误信息
    - done: 流结束
    """

    type: Literal[
        "text",
        "tool_call_start",
        "tool_call_complete",
        "error",
        "done",
    ]
    content: str | dict
    metadata: dict[str, Any] = {}


class LLMProvider(ABC):
    """
    LLM Provider抽象接口

    所有LLM provider必须实现此接口。
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        生成响应（非流式）

        Args:
            messages: 对话历史
            tools: 可用工具列表
            **kwargs: 额外参数（如temperature, max_tokens等）

        Returns:
            LLM响应
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        生成流式响应

        Args:
            messages: 对话历史
            tools: 可用工具列表
            **kwargs: 额外参数

        Yields:
            StreamChunk事件
        """
        if False:
            yield  # type: ignore[unreachable]
        raise NotImplementedError

    def get_token_counter(self):
        """
        获取 Token 计数器

        默认返回 EstimateCounter，子类可以覆盖以提供更精确的计数器。

        Returns:
            TokenCounter 实例
        """
        from loom.memory.tokenizer import EstimateCounter

        return EstimateCounter()
