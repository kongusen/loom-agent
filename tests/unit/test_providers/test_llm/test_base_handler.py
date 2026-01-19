"""
Base Response Handler Unit Tests

测试LLM响应处理器基类的核心功能
"""

from loom.providers.llm.base_handler import BaseResponseHandler, ToolCallAggregator
from loom.providers.llm.interface import StreamChunk


class TestToolCallAggregatorInit:
    """测试ToolCallAggregator初始化"""

    def test_init(self):
        """测试初始化"""
        aggregator = ToolCallAggregator()

        assert aggregator.buffer == {}
        assert aggregator.started == {}


class TestToolCallAggregatorAddChunk:
    """测试add_chunk方法"""

    def test_add_chunk_first_call(self):
        """测试添加第一个chunk"""
        aggregator = ToolCallAggregator()

        result = aggregator.add_chunk(
            index=0, tool_id="call_123", name="get_weather", arguments='{"city":'
        )

        # 第一次添加name时应该返回tool_call_start事件
        assert result is not None
        assert result.type == "tool_call_start"
        assert result.content["id"] == "call_123"
        assert result.content["name"] == "get_weather"
        assert result.content["index"] == 0

    def test_add_chunk_subsequent_calls(self):
        """测试添加后续chunks"""
        aggregator = ToolCallAggregator()

        # 第一次添加
        aggregator.add_chunk(index=0, tool_id="call_123", name="get_weather")

        # 后续添加arguments
        result = aggregator.add_chunk(index=0, arguments=' "Beijing"')

        # 后续添加不应该返回start事件
        assert result is None

        # 验证arguments被累积
        assert aggregator.buffer[0]["arguments"] == ' "Beijing"'

    def test_add_chunk_multiple_indices(self):
        """测试添加多个工具调用"""
        aggregator = ToolCallAggregator()

        result1 = aggregator.add_chunk(index=0, tool_id="call_1", name="tool1")
        result2 = aggregator.add_chunk(index=1, tool_id="call_2", name="tool2")

        assert result1 is not None
        assert result2 is not None
        assert len(aggregator.buffer) == 2


class TestToolCallAggregatorGetCompleteCalls:
    """测试get_complete_calls方法"""

    def test_get_complete_calls_valid_json(self):
        """测试获取有效的完整工具调用"""
        aggregator = ToolCallAggregator()

        # 添加完整的工具调用
        aggregator.add_chunk(index=0, tool_id="call_123", name="get_weather")
        aggregator.add_chunk(index=0, arguments='{"city": "Beijing"}')

        # 获取完整调用
        calls = list(aggregator.get_complete_calls())

        assert len(calls) == 1
        assert calls[0].type == "tool_call_complete"
        assert calls[0].content["id"] == "call_123"
        assert calls[0].content["name"] == "get_weather"
        assert calls[0].content["arguments"] == '{"city": "Beijing"}'

    def test_get_complete_calls_invalid_json(self):
        """测试获取无效JSON的工具调用"""
        aggregator = ToolCallAggregator()

        # 添加无效JSON的工具调用
        aggregator.add_chunk(index=0, tool_id="call_123", name="get_weather")
        aggregator.add_chunk(index=0, arguments='{"city": invalid}')

        # 获取完整调用
        calls = list(aggregator.get_complete_calls())

        assert len(calls) == 1
        assert calls[0].type == "error"
        assert calls[0].content["error"] == "invalid_tool_arguments"
        assert "get_weather" in calls[0].content["message"]

    def test_get_complete_calls_incomplete(self):
        """测试获取不完整的工具调用"""
        aggregator = ToolCallAggregator()

        # 只添加部分信息（缺少name）
        aggregator.add_chunk(index=0, tool_id="call_123")

        # 获取完整调用
        calls = list(aggregator.get_complete_calls())

        # 不完整的调用不应该被返回
        assert len(calls) == 0


class TestToolCallAggregatorClear:
    """测试clear方法"""

    def test_clear(self):
        """测试清空缓冲区"""
        aggregator = ToolCallAggregator()

        # 添加一些数据
        aggregator.add_chunk(index=0, tool_id="call_123", name="get_weather")
        aggregator.add_chunk(index=1, tool_id="call_456", name="get_time")

        # 清空
        aggregator.clear()

        assert aggregator.buffer == {}
        assert aggregator.started == {}


class TestBaseResponseHandler:
    """测试BaseResponseHandler"""

    def test_init(self):
        """测试初始化"""

        # 创建一个具体的子类用于测试
        class TestHandler(BaseResponseHandler):
            async def stream_response(self, response):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = TestHandler()
        assert isinstance(handler.aggregator, ToolCallAggregator)

    def test_create_error_chunk(self):
        """测试创建错误chunk"""

        class TestHandler(BaseResponseHandler):
            async def stream_response(self, response):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = TestHandler()
        error = ValueError("Test error")
        chunk = handler.create_error_chunk(error)

        assert chunk.type == "error"
        assert chunk.content["error"] == "stream_error"
        assert chunk.content["message"] == "Test error"
        assert chunk.content["type"] == "ValueError"

    def test_create_error_chunk_with_context(self):
        """测试创建带上下文的错误chunk"""

        class TestHandler(BaseResponseHandler):
            async def stream_response(self, response):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = TestHandler()
        error = ValueError("Test error")
        context = {"request_id": "123"}
        chunk = handler.create_error_chunk(error, context)

        assert chunk.content["context"] == {"request_id": "123"}

    def test_create_done_chunk(self):
        """测试创建完成chunk"""

        class TestHandler(BaseResponseHandler):
            async def stream_response(self, response):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = TestHandler()
        chunk = handler.create_done_chunk("stop")

        assert chunk.type == "done"
        assert chunk.content == ""
        assert chunk.metadata["finish_reason"] == "stop"

    def test_create_done_chunk_with_token_usage(self):
        """测试创建带token使用统计的完成chunk"""

        class TestHandler(BaseResponseHandler):
            async def stream_response(self, response):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = TestHandler()
        token_usage = {"prompt_tokens": 10, "completion_tokens": 20}
        chunk = handler.create_done_chunk("stop", token_usage)

        assert chunk.metadata["token_usage"] == token_usage
