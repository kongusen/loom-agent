"""
Base Response Handler for LLM Providers

提供通用的响应处理逻辑，包括：
- 流式工具调用聚合
- JSON 验证
- 错误处理
- Token 使用统计
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterator
from typing import Any

from loom.llm.interface import StreamChunk

logger = logging.getLogger(__name__)


class ToolCallAggregator:
    """
    工具调用聚合器

    用于聚合流式 API 中分散的工具调用片段
    """

    def __init__(self):
        self.buffer: dict[int, dict[str, Any]] = {}
        self.started: dict[int, bool] = {}

    def add_chunk(
        self,
        index: int,
        tool_id: str | None = None,
        name: str | None = None,
        arguments: str | None = None
    ) -> StreamChunk | None:
        """
        添加工具调用片段

        Returns:
            如果是新工具调用，返回 tool_call_start 事件；否则返回 None
        """
        # 初始化缓冲区
        if index not in self.buffer:
            self.buffer[index] = {
                "id": "",
                "name": "",
                "arguments": ""
            }
            self.started[index] = False

        # 聚合内容
        if tool_id:
            self.buffer[index]["id"] = tool_id
        if name:
            self.buffer[index]["name"] = name
        if arguments:
            self.buffer[index]["arguments"] += arguments

        # 如果有名称且未发送 start 事件，发送它
        if self.buffer[index]["name"] and not self.started[index]:
            self.started[index] = True
            return StreamChunk(
                type="tool_call_start",
                content={
                    "id": self.buffer[index]["id"],
                    "name": self.buffer[index]["name"],
                    "index": index
                },
                metadata={}
            )

        return None

    def get_complete_calls(self) -> Iterator[StreamChunk]:
        """
        获取所有完成的工具调用

        Yields:
            tool_call_complete 或 error 事件
        """
        for idx, tc in self.buffer.items():
            if not tc.get("id") or not tc.get("name"):
                continue

            # 验证 arguments 是否是有效 JSON
            try:
                json.loads(tc["arguments"])
                yield StreamChunk(
                    type="tool_call_complete",
                    content=tc,
                    metadata={"index": idx}
                )
            except json.JSONDecodeError as e:
                logger.error(
                    f"Invalid JSON in tool {tc['name']} arguments: {str(e)}"
                )
                yield StreamChunk(
                    type="error",
                    content={
                        "error": "invalid_tool_arguments",
                        "message": f"Tool {tc['name']} arguments are not valid JSON: {str(e)}",
                        "tool_call": tc
                    },
                    metadata={"index": idx}
                )

    def clear(self):
        """清空缓冲区"""
        self.buffer.clear()
        self.started.clear()


class BaseResponseHandler(ABC):
    """
    LLM 响应处理器基类

    提供通用的响应处理逻辑，子类需要实现特定提供商的适配
    """

    def __init__(self):
        self.aggregator = ToolCallAggregator()

    @abstractmethod
    async def stream_response(
        self,
        response: Any
    ) -> AsyncGenerator[StreamChunk, None]:  # Ideally this should be AsyncGenerator but matching abstract definition
        """
        处理单个流式响应块

        子类需要实现此方法，将提供商特定的 chunk 转换为标准 StreamChunk

        Args:
            chunk: 提供商特定的响应块

        Yields:
            标准化的 StreamChunk
        """
        pass

    def create_error_chunk(
        self,
        error: Exception,
        context: dict[str, Any] | None = None
    ) -> StreamChunk:
        """
        创建错误事件

        Args:
            error: 异常对象
            context: 额外的上下文信息

        Returns:
            error 类型的 StreamChunk
        """
        return StreamChunk(
            type="error",
            content={
                "error": "stream_error",
                "message": str(error),
                "type": type(error).__name__,
                "context": context or {}
            },
            metadata={}
        )

    def create_done_chunk(
        self,
        finish_reason: str,
        token_usage: dict[str, int] | None = None
    ) -> StreamChunk:
        """
        创建完成事件

        Args:
            finish_reason: 完成原因
            token_usage: Token 使用统计

        Returns:
            done 类型的 StreamChunk
        """
        metadata: dict[str, Any] = {"finish_reason": finish_reason}
        if token_usage:
            metadata["token_usage"] = token_usage

        return StreamChunk(
            type="done",
            content="",
            metadata=metadata
        )
