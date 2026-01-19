"""
Mock LLM Provider Unit Tests

测试Mock LLM Provider的核心功能
"""

import pytest

from loom.providers.llm.interface import LLMResponse
from loom.providers.llm.mock import MockLLMProvider


class TestMockLLMProviderChat:
    """测试chat方法"""

    @pytest.mark.asyncio
    async def test_chat_normal_message(self):
        """测试普通消息"""
        provider = MockLLMProvider()
        messages = [{"role": "user", "content": "Hello"}]

        response = await provider.chat(messages)

        assert isinstance(response, LLMResponse)
        assert "hello" in response.content.lower()
        assert response.tool_calls is None or len(response.tool_calls) == 0

    @pytest.mark.asyncio
    async def test_chat_with_search_keyword(self):
        """测试包含search关键词的消息"""
        provider = MockLLMProvider()
        messages = [{"role": "user", "content": "search for Python"}]

        response = await provider.chat(messages)

        assert response.content == ""
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["name"] == "search"
        assert response.tool_calls[0]["arguments"]["query"] == "for python"


class TestMockLLMProviderStreamChat:
    """测试stream_chat方法"""

    @pytest.mark.asyncio
    async def test_stream_chat_normal_message(self):
        """测试普通消息的流式响应"""
        provider = MockLLMProvider()
        messages = [{"role": "user", "content": "Hello"}]

        chunks = []
        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        # 应该有3个文本chunk + 1个done chunk
        assert len(chunks) == 4
        assert chunks[0].type == "text"
        assert chunks[1].type == "text"
        assert chunks[2].type == "text"
        assert chunks[3].type == "done"

    @pytest.mark.asyncio
    async def test_stream_chat_with_search_keyword(self):
        """测试包含search关键词的流式响应"""
        provider = MockLLMProvider()
        messages = [{"role": "user", "content": "search for AI"}]

        chunks = []
        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        # 应该有tool_call_start + tool_call_complete + done
        assert len(chunks) == 3
        assert chunks[0].type == "tool_call_start"
        assert chunks[0].content["name"] == "search"
        assert chunks[1].type == "tool_call_complete"
        assert chunks[1].content["arguments"]["query"] == "for ai"
        assert chunks[2].type == "done"

    @pytest.mark.asyncio
    async def test_stream_chat_with_calculate_keyword(self):
        """测试包含calculate关键词的流式响应"""
        provider = MockLLMProvider()
        messages = [{"role": "user", "content": "calculate 2+2"}]

        chunks = []
        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        # 应该有tool_call_start + tool_call_complete + done
        assert len(chunks) == 3
        assert chunks[0].type == "tool_call_start"
        assert chunks[0].content["name"] == "mock-calculator"
        assert chunks[1].type == "tool_call_complete"
        assert chunks[2].type == "done"
