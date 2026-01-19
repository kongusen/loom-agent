"""
OpenAI Provider Unit Tests

测试OpenAI Provider的核心功能
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from loom.config import LLMConfig
from loom.providers.llm.interface import LLMResponse
from loom.providers.llm.openai import OpenAIProvider


class TestOpenAIProviderInit:
    """测试OpenAIProvider初始化"""

    def test_init_with_api_key(self):
        """测试使用api_key初始化"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        assert provider.model == "gpt-4"
        assert provider.temperature == 0.7
        assert provider.max_tokens is None
        assert provider.client is not None

    def test_init_with_custom_parameters(self):
        """测试使用自定义参数初始化"""
        provider = OpenAIProvider(
            LLMConfig(
                provider="openai",
                api_key="sk-test123",
                model="gpt-3.5-turbo",
                temperature=0.5,
                max_tokens=1000,
            )
        )

        assert provider.model == "gpt-3.5-turbo"
        assert provider.temperature == 0.5
        assert provider.max_tokens == 1000

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"})
    def test_init_with_env_api_key(self):
        """测试从环境变量获取api_key（用户控制配置来源）"""
        # 新架构：用户从环境变量读取并显式传递给配置
        api_key = os.environ.get("OPENAI_API_KEY")
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key=api_key)
        )

        assert provider.client is not None


class TestOpenAIProviderGetTokenCounter:
    """测试get_token_counter方法"""

    def test_get_token_counter(self):
        """测试获取token计数器"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )
        counter = provider.get_token_counter()

        from loom.memory.tokenizer import TiktokenCounter

        assert isinstance(counter, TiktokenCounter)


class TestOpenAIProviderConvertTools:
    """测试_convert_tools方法"""

    def test_convert_tools_openai_format(self):
        """测试转换已经是OpenAI格式的工具"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather info",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        result = provider._convert_tools(tools)

        assert len(result) == 1
        assert result[0] == tools[0]

    def test_convert_tools_mcp_format(self):
        """测试转换MCP格式的工具"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )
        tools = [
            {
                "name": "search",
                "description": "Search the web",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            }
        ]

        result = provider._convert_tools(tools)

        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "search"
        assert result[0]["function"]["description"] == "Search the web"
        assert result[0]["function"]["parameters"]["type"] == "object"


class TestOpenAIProviderChat:
    """测试chat方法"""

    @pytest.mark.asyncio
    async def test_chat_basic_message(self):
        """测试基本消息的chat调用"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Hello! How can I help?"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [{"role": "user", "content": "Hello"}]
        response = await provider.chat(messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "Hello! How can I help?"
        assert response.tool_calls == []
        assert response.token_usage["prompt_tokens"] == 10

    @pytest.mark.asyncio
    async def test_chat_with_tool_calls(self):
        """测试带工具调用的chat响应"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        # Mock tool call
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function = Mock()
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"city": "Beijing"}'

        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = ""
        mock_response.choices[0].message.tool_calls = [mock_tool_call]
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 25
        mock_response.usage.total_tokens = 40

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [{"role": "user", "content": "What's the weather?"}]
        tools = [{"name": "get_weather", "description": "Get weather"}]
        response = await provider.chat(messages, tools=tools)

        assert response.content == ""
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["id"] == "call_123"
        assert response.tool_calls[0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_chat_with_custom_parameters(self):
        """测试使用自定义参数的chat调用"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123", model="gpt-4", temperature=0.5)
        )

        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Response"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage = None

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [{"role": "user", "content": "Test"}]
        response = await provider.chat(messages, temperature=0.8, max_tokens=100)

        # Verify the API was called with custom parameters
        call_args = provider.client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.8
        assert call_args[1]["max_tokens"] == 100
        assert response.token_usage is None


class TestOpenAIProviderStreamChat:
    """测试stream_chat方法"""

    @pytest.mark.asyncio
    async def test_stream_chat_basic(self):
        """测试基本的流式响应"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        # Mock streaming chunks
        async def mock_stream():
            # Text chunk
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.choices[0].delta = Mock()
            chunk1.choices[0].delta.content = "Hello"
            chunk1.choices[0].delta.tool_calls = None
            chunk1.choices[0].finish_reason = None
            yield chunk1

            # Finish chunk
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.choices[0].delta = Mock()
            chunk2.choices[0].delta.content = None
            chunk2.choices[0].delta.tool_calls = None
            chunk2.choices[0].finish_reason = "stop"
            chunk2.usage = Mock()
            chunk2.usage.prompt_tokens = 5
            chunk2.usage.completion_tokens = 10
            chunk2.usage.total_tokens = 15
            yield chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        messages = [{"role": "user", "content": "Hi"}]
        chunks = []
        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].type == "text"
        assert chunks[0].content == "Hello"
        assert chunks[1].type == "done"

    @pytest.mark.asyncio
    async def test_stream_chat_with_tool_calls(self):
        """测试流式响应中的工具调用"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        # Mock streaming chunks with tool calls
        async def mock_stream():
            # Tool call start chunk
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.choices[0].delta = Mock()
            chunk1.choices[0].delta.content = None
            chunk1.choices[0].delta.tool_calls = [Mock()]
            chunk1.choices[0].delta.tool_calls[0].index = 0
            chunk1.choices[0].delta.tool_calls[0].id = "call_123"
            chunk1.choices[0].delta.tool_calls[0].function = Mock()
            chunk1.choices[0].delta.tool_calls[0].function.name = "search"
            chunk1.choices[0].delta.tool_calls[0].function.arguments = '{"query":'
            chunk1.choices[0].finish_reason = None
            yield chunk1

            # Tool call continuation chunk
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.choices[0].delta = Mock()
            chunk2.choices[0].delta.content = None
            chunk2.choices[0].delta.tool_calls = [Mock()]
            chunk2.choices[0].delta.tool_calls[0].index = 0
            chunk2.choices[0].delta.tool_calls[0].id = None
            chunk2.choices[0].delta.tool_calls[0].function = Mock()
            chunk2.choices[0].delta.tool_calls[0].function.name = None
            chunk2.choices[0].delta.tool_calls[0].function.arguments = ' "test"}'
            chunk2.choices[0].finish_reason = None
            yield chunk2

            # Finish chunk
            chunk3 = Mock()
            chunk3.choices = [Mock()]
            chunk3.choices[0].delta = Mock()
            chunk3.choices[0].delta.content = None
            chunk3.choices[0].delta.tool_calls = None
            chunk3.choices[0].finish_reason = "tool_calls"
            chunk3.usage = None
            yield chunk3

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        messages = [{"role": "user", "content": "Search for test"}]
        chunks = []
        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        # Should have: tool_call_start, tool_call_complete, done
        assert len(chunks) == 3
        assert chunks[0].type == "tool_call_start"
        assert chunks[0].content["name"] == "search"
        assert chunks[1].type == "tool_call_complete"
        assert chunks[2].type == "done"

    @pytest.mark.asyncio
    async def test_stream_chat_error_handling(self):
        """测试流式响应中的错误处理"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        # Mock streaming that raises an error
        async def mock_stream():
            raise ValueError("API Error")
            yield  # This line is never reached

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        messages = [{"role": "user", "content": "Test"}]
        chunks = []
        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        # Should have an error chunk
        assert len(chunks) == 1
        assert chunks[0].type == "error"
        assert "API Error" in chunks[0].content["message"]

    @pytest.mark.asyncio
    async def test_stream_chat_usage_only_chunk(self):
        """测试只包含usage的chunk"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        # Mock streaming with usage-only chunk
        async def mock_stream():
            # Usage-only chunk (no choices)
            chunk1 = Mock()
            chunk1.choices = []
            chunk1.usage = Mock()
            chunk1.usage.prompt_tokens = 10
            chunk1.usage.completion_tokens = 20
            chunk1.usage.total_tokens = 30
            yield chunk1

            # Regular finish chunk
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.choices[0].delta = Mock()
            chunk2.choices[0].delta.content = None
            chunk2.choices[0].delta.tool_calls = None
            chunk2.choices[0].finish_reason = "stop"
            chunk2.usage = None
            yield chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        messages = [{"role": "user", "content": "Test"}]
        chunks = []
        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        # Should have: usage_only done chunk, regular done chunk
        assert len(chunks) == 2
        assert chunks[0].type == "done"
        assert chunks[0].metadata["finish_reason"] == "usage_only"
        assert chunks[0].metadata["token_usage"]["total_tokens"] == 30
        assert chunks[1].type == "done"


class TestOpenAIProviderStreamResponse:
    """测试stream_response方法"""

    @pytest.mark.asyncio
    async def test_stream_response_basic(self):
        """测试基本的stream_response处理"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        # Mock streaming response
        async def mock_response():
            # Text chunk
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.choices[0].delta = Mock()
            chunk1.choices[0].delta.content = "Test"
            chunk1.choices[0].delta.tool_calls = None
            chunk1.choices[0].finish_reason = None
            yield chunk1

            # Finish chunk
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.choices[0].delta = Mock()
            chunk2.choices[0].delta.content = None
            chunk2.choices[0].delta.tool_calls = None
            chunk2.choices[0].finish_reason = "stop"
            chunk2.usage = Mock()
            chunk2.usage.prompt_tokens = 5
            chunk2.usage.completion_tokens = 10
            chunk2.usage.total_tokens = 15
            yield chunk2

        chunks = []
        async for chunk in provider.stream_response(mock_response()):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].type == "text"
        assert chunks[0].content == "Test"
        assert chunks[1].type == "done"

    @pytest.mark.asyncio
    async def test_stream_response_with_tool_calls(self):
        """测试stream_response中的工具调用处理"""
        provider = OpenAIProvider(
            LLMConfig(provider="openai", api_key="sk-test123")
        )

        # Mock streaming response with tool calls
        async def mock_response():
            # Tool call chunk
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.choices[0].delta = Mock()
            chunk1.choices[0].delta.content = None
            chunk1.choices[0].delta.tool_calls = [Mock()]
            chunk1.choices[0].delta.tool_calls[0].index = 0
            chunk1.choices[0].delta.tool_calls[0].id = "call_456"
            chunk1.choices[0].delta.tool_calls[0].function = Mock()
            chunk1.choices[0].delta.tool_calls[0].function.name = "calculator"
            chunk1.choices[0].delta.tool_calls[0].function.arguments = '{"expr": "2+2"}'
            chunk1.choices[0].finish_reason = None
            yield chunk1

            # Finish chunk
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.choices[0].delta = Mock()
            chunk2.choices[0].delta.content = None
            chunk2.choices[0].delta.tool_calls = None
            chunk2.choices[0].finish_reason = "tool_calls"
            chunk2.usage = None
            yield chunk2

        chunks = []
        async for chunk in provider.stream_response(mock_response()):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0].type == "tool_call_start"
        assert chunks[1].type == "tool_call_complete"
        assert chunks[2].type == "done"
