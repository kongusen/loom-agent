"""
Streaming Protocol - 流式输出规范

基于公理系统和唯一性原则：
定义统一的流式输出规范，所有使用流式输出的组件都必须遵循此规范。

设计原则：
1. 唯一性 - 流式输出规范只在一个地方定义
2. 标准化 - 所有流式输出都使用相同的接口
3. 可扩展 - 支持不同类型的流式内容

流式输出类型：
- text: 文本内容
- tool_call_start: 工具调用开始
- tool_call_complete: 工具调用完成
- error: 错误信息
- done: 流结束
"""

from collections.abc import AsyncIterator
from typing import Any, Protocol

from loom.providers.llm.interface import StreamChunk


class StreamingProtocol(Protocol):
    """
    流式输出规范

    所有支持流式输出的组件都必须实现此协议。
    """

    async def stream_output(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式输出

        Args:
            task_id: 任务ID
            **kwargs: 其他参数

        Yields:
            StreamChunk对象
        """
        ...


class StreamingMixin:
    """
    流式输出混入类

    提供流式输出的通用功能。
    """

    async def _stream_text(
        self,
        content: str,
        task_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> StreamChunk:
        """
        创建文本流式chunk

        Args:
            content: 文本内容
            task_id: 任务ID
            metadata: 元数据

        Returns:
            StreamChunk对象
        """
        # 如果有event_bus，发布thinking事件
        if hasattr(self, "event_bus") and hasattr(self, "publish_thinking"):
            await self.publish_thinking(  # type: ignore
                content=content,
                task_id=task_id,
                metadata=metadata,
            )

        return StreamChunk(
            type="text",
            content=content,
            metadata=metadata or {},
        )

    async def _stream_tool_call_start(
        self,
        tool_name: str,
        tool_id: str,
        index: int,
        task_id: str,
    ) -> StreamChunk:
        """
        创建工具调用开始chunk

        Args:
            tool_name: 工具名称
            tool_id: 工具调用ID
            index: 工具调用索引
            task_id: 任务ID

        Returns:
            StreamChunk对象
        """
        # 如果有event_bus，发布thinking事件
        if hasattr(self, "event_bus") and hasattr(self, "publish_thinking"):
            await self.publish_thinking(  # type: ignore
                content=f"🔧 Calling tool: {tool_name}",
                task_id=task_id,
                metadata={"tool_name": tool_name, "tool_id": tool_id},
            )

        return StreamChunk(
            type="tool_call_start",
            content={"name": tool_name, "id": tool_id, "index": index},
            metadata={},
        )

    async def _stream_tool_call_complete(
        self,
        tool_name: str,
        tool_id: str,
        tool_args: dict[str, Any],
        task_id: str,
    ) -> StreamChunk:
        """
        创建工具调用完成chunk

        Args:
            tool_name: 工具名称
            tool_id: 工具调用ID
            tool_args: 工具参数
            task_id: 任务ID

        Returns:
            StreamChunk对象
        """
        # 如果有event_bus，发布tool_call事件
        if hasattr(self, "event_bus") and hasattr(self, "publish_tool_call"):
            await self.publish_tool_call(  # type: ignore
                tool_name=tool_name,
                tool_args=tool_args,
                task_id=task_id,
            )

        return StreamChunk(
            type="tool_call_complete",
            content={
                "name": tool_name,
                "id": tool_id,
                "arguments": tool_args,
            },
            metadata={},
        )

    async def _stream_error(
        self,
        error: Exception,
        task_id: str,
    ) -> StreamChunk:
        """
        创建错误chunk

        Args:
            error: 错误对象
            task_id: 任务ID

        Returns:
            StreamChunk对象
        """
        # 如果有event_bus，发布error事件
        if hasattr(self, "event_bus") and hasattr(self, "_publish_event"):
            await self._publish_event(  # type: ignore
                action="node.stream_error",
                parameters={"error": str(error)},
                task_id=task_id,
            )

        return StreamChunk(
            type="error",
            content={
                "error": "stream_error",
                "message": str(error),
                "type": type(error).__name__,
            },
            metadata={},
        )

    async def _stream_done(
        self,
        finish_reason: str = "stop",
        token_usage: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> StreamChunk:
        """
        创建完成chunk

        Args:
            finish_reason: 完成原因
            token_usage: token使用统计
            task_id: 任务ID

        Returns:
            StreamChunk对象
        """
        # 如果有event_bus和token_usage，发布token_usage事件
        if (
            token_usage
            and task_id
            and hasattr(self, "event_bus")
            and hasattr(self, "_publish_event")
        ):
            await self._publish_event(  # type: ignore
                action="node.token_usage",
                parameters={"token_usage": token_usage},
                task_id=task_id,
            )

        metadata = {"finish_reason": finish_reason}
        if token_usage:
            metadata["token_usage"] = token_usage

        return StreamChunk(
            type="done",
            content="",
            metadata=metadata,
        )
