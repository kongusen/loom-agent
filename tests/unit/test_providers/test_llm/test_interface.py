"""
LLM Provider Interface Unit Tests

测试LLM Provider接口的核心功能
"""

from loom.providers.llm.interface import LLMProvider, LLMResponse, StreamChunk


class TestLLMResponse:
    """测试LLMResponse模型"""

    def test_create_minimal(self):
        """测试最小参数创建"""
        response = LLMResponse(content="Hello")

        assert response.content == "Hello"
        assert response.tool_calls == []
        assert response.token_usage is None

    def test_create_with_tool_calls(self):
        """测试带工具调用创建"""
        tool_calls = [{"name": "search", "arguments": {"query": "test"}}]
        response = LLMResponse(content="", tool_calls=tool_calls)

        assert response.content == ""
        assert response.tool_calls == tool_calls

    def test_create_with_token_usage(self):
        """测试带token使用统计创建"""
        token_usage = {"prompt_tokens": 10, "completion_tokens": 20}
        response = LLMResponse(content="Hello", token_usage=token_usage)

        assert response.token_usage == token_usage


class TestStreamChunk:
    """测试StreamChunk模型"""

    def test_create_text_chunk(self):
        """测试创建文本chunk"""
        chunk = StreamChunk(type="text", content="Hello")

        assert chunk.type == "text"
        assert chunk.content == "Hello"
        assert chunk.metadata == {}

    def test_create_tool_call_start_chunk(self):
        """测试创建工具调用开始chunk"""
        content = {"name": "search", "id": "call_123", "index": 0}
        chunk = StreamChunk(type="tool_call_start", content=content)

        assert chunk.type == "tool_call_start"
        assert chunk.content == content

    def test_create_chunk_with_metadata(self):
        """测试创建带metadata的chunk"""
        metadata = {"index": 0, "total": 10}
        chunk = StreamChunk(type="text", content="test", metadata=metadata)

        assert chunk.metadata == metadata


class TestLLMProvider:
    """测试LLMProvider基类"""

    def test_get_token_counter(self):
        """测试get_token_counter方法"""

        # 创建一个具体的子类用于测试
        class TestProvider(LLMProvider):
            async def chat(self, messages, tools=None, **kwargs):
                return LLMResponse(content="test")

            async def stream_chat(self, messages, tools=None, **kwargs):
                yield StreamChunk(type="text", content="test", metadata={})

        provider = TestProvider()
        counter = provider.get_token_counter()

        # 验证返回的是EstimateCounter实例
        from loom.memory.tokenizer import EstimateCounter

        assert isinstance(counter, EstimateCounter)
