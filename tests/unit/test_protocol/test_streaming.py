"""
Streaming Protocol Unit Tests

测试流式输出协议
"""

from unittest.mock import AsyncMock

import pytest

from loom.protocol.streaming import StreamingMixin
from loom.providers.llm.interface import StreamChunk


class TestStreamingMixin:
    """测试StreamingMixin混入类"""

    @pytest.mark.asyncio
    async def test_stream_text_basic(self):
        """测试基本文本流式输出"""
        mixin = StreamingMixin()

        chunk = await mixin._stream_text(
            content="Test content",
            task_id="task-1",
        )

        assert isinstance(chunk, StreamChunk)
        assert chunk.type == "text"
        assert chunk.content == "Test content"
        assert chunk.metadata == {}

    @pytest.mark.asyncio
    async def test_stream_text_with_metadata(self):
        """测试带元数据的文本流式输出"""
        mixin = StreamingMixin()

        chunk = await mixin._stream_text(
            content="Test content",
            task_id="task-1",
            metadata={"key": "value"},
        )

        assert chunk.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_stream_tool_call_start(self):
        """测试工具调用开始"""
        mixin = StreamingMixin()

        chunk = await mixin._stream_tool_call_start(
            tool_name="test_tool",
            tool_id="tool-123",
            index=0,
            task_id="task-1",
        )

        assert chunk.type == "tool_call_start"
        assert chunk.content["name"] == "test_tool"
        assert chunk.content["id"] == "tool-123"
        assert chunk.content["index"] == 0

    @pytest.mark.asyncio
    async def test_stream_tool_call_complete(self):
        """测试工具调用完成"""
        mixin = StreamingMixin()

        chunk = await mixin._stream_tool_call_complete(
            tool_name="test_tool",
            tool_id="tool-123",
            tool_args={"arg1": "value1"},
            task_id="task-1",
        )

        assert chunk.type == "tool_call_complete"
        assert chunk.content["name"] == "test_tool"
        assert chunk.content["id"] == "tool-123"
        assert chunk.content["arguments"] == {"arg1": "value1"}

    @pytest.mark.asyncio
    async def test_stream_error(self):
        """测试错误流式输出"""
        mixin = StreamingMixin()
        error = ValueError("Test error")

        chunk = await mixin._stream_error(
            error=error,
            task_id="task-1",
        )

        assert chunk.type == "error"
        assert chunk.content["error"] == "stream_error"
        assert chunk.content["message"] == "Test error"
        assert chunk.content["type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_stream_done_basic(self):
        """测试基本完成流式输出"""
        mixin = StreamingMixin()

        chunk = await mixin._stream_done()

        assert chunk.type == "done"
        assert chunk.content == ""
        assert chunk.metadata["finish_reason"] == "stop"
        assert "token_usage" not in chunk.metadata

    @pytest.mark.asyncio
    async def test_stream_done_with_token_usage(self):
        """测试带token使用统计的完成流式输出"""
        mixin = StreamingMixin()

        chunk = await mixin._stream_done(
            finish_reason="length",
            token_usage={"input": 100, "output": 50},
            task_id="task-1",
        )

        assert chunk.metadata["finish_reason"] == "length"
        assert chunk.metadata["token_usage"] == {"input": 100, "output": 50}


class TestStreamingMixinWithEventBus:
    """测试带EventBus的StreamingMixin（触发事件发布分支）"""

    @pytest.mark.asyncio
    async def test_stream_text_with_event_bus(self):
        """测试带event_bus的文本流式输出（触发line 77）"""
        mixin = StreamingMixin()
        # 模拟event_bus和publish_thinking方法
        mixin.publish_thinking = AsyncMock()
        mixin.event_bus = AsyncMock()

        chunk = await mixin._stream_text(
            content="Thinking content",
            task_id="task-1",
            metadata={"source": "thought"},
        )

        assert chunk.type == "text"
        assert chunk.content == "Thinking content"
        # 验证发布了thinking事件
        mixin.publish_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_tool_call_start_with_event_bus(self):
        """测试带event_bus的工具调用开始（触发line 110）"""
        mixin = StreamingMixin()
        mixin.publish_thinking = AsyncMock()
        mixin.event_bus = AsyncMock()

        chunk = await mixin._stream_tool_call_start(
            tool_name="test_tool",
            tool_id="tool-123",
            index=0,
            task_id="task-1",
        )

        assert chunk.type == "tool_call_start"
        # 验证发布了tool调用thinking事件
        mixin.publish_thinking.assert_called_once()
        call_args = mixin.publish_thinking.call_args
        assert "tool_name" in call_args.kwargs.get("metadata", {})

    @pytest.mark.asyncio
    async def test_stream_tool_call_complete_with_event_bus(self):
        """测试带event_bus的工具调用完成（触发line 143）"""
        mixin = StreamingMixin()
        mixin.publish_tool_call = AsyncMock()
        mixin.event_bus = AsyncMock()

        chunk = await mixin._stream_tool_call_complete(
            tool_name="test_tool",
            tool_id="tool-123",
            tool_args={"arg1": "value1"},
            task_id="task-1",
        )

        assert chunk.type == "tool_call_complete"
        # 验证发布了tool_call事件
        mixin.publish_tool_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_error_with_event_bus(self):
        """测试带event_bus的错误流式输出（触发line 176）"""
        mixin = StreamingMixin()
        mixin._publish_event = AsyncMock()
        mixin.event_bus = AsyncMock()

        error = ValueError("Test error")
        chunk = await mixin._stream_error(
            error=error,
            task_id="task-1",
        )

        assert chunk.type == "error"
        # 验证发布了错误事件
        mixin._publish_event.assert_called_once()
        call_args = mixin._publish_event.call_args
        assert call_args.kwargs.get("action") == "node.stream_error"

    @pytest.mark.asyncio
    async def test_stream_done_with_token_usage_and_event_bus(self):
        """测试带token使用和event_bus的完成流式输出（触发line 216）"""
        mixin = StreamingMixin()
        mixin._publish_event = AsyncMock()
        mixin.event_bus = AsyncMock()

        chunk = await mixin._stream_done(
            token_usage={"input": 100, "output": 50},
            task_id="task-1",
        )

        assert chunk.type == "done"
        # 验证发布了token_usage事件
        mixin._publish_event.assert_called_once()
        call_args = mixin._publish_event.call_args
        assert call_args.kwargs.get("action") == "node.token_usage"

