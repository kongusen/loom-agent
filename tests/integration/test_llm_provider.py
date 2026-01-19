"""
LLM Provider 集成测试

测试真实API调用。需要配置环境变量才能运行：
- OPENAI_API_KEY: OpenAI API密钥
- ENABLE_REAL_API_TESTS=true: 启用真实API测试

运行方式：
    pytest tests/integration/test_llm_provider.py -v
"""

import pytest

from loom.config import LLMConfig
from loom.providers.llm.openai import OpenAIProvider
from tests.api_config import requires_real_api


class TestOpenAIProviderIntegration:
    """OpenAI Provider 真实API集成测试"""

    @requires_real_api
    @pytest.mark.asyncio
    async def test_chat_basic(self, openai_config):
        """测试基本的chat调用"""
        provider = OpenAIProvider(
            LLMConfig(
                provider="openai",
                api_key=openai_config["api_key"],
                base_url=openai_config["base_url"],
                model=openai_config["model"],
                timeout=openai_config["timeout"],
                max_retries=openai_config["max_retries"],
            )
        )

        messages = [{"role": "user", "content": "Say 'Hello, World!' and nothing else."}]

        response = await provider.chat(messages)

        # 验证响应
        assert response.content is not None
        assert len(response.content) > 0
        assert "Hello" in response.content or "hello" in response.content

    @requires_real_api
    @pytest.mark.asyncio
    async def test_chat_with_system_message(self, openai_config):
        """测试带系统消息的chat调用"""
        provider = OpenAIProvider(
            LLMConfig(
                provider="openai",
                api_key=openai_config["api_key"],
                base_url=openai_config["base_url"],
                model=openai_config["model"],
            )
        )

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that responds in one sentence.",
            },
            {"role": "user", "content": "What is 2+2?"},
        ]

        response = await provider.chat(messages)

        # 验证响应
        assert response.content is not None
        assert "4" in response.content

    @requires_real_api
    @pytest.mark.asyncio
    async def test_stream_chat_basic(self, openai_config):
        """测试基本的stream_chat调用"""
        provider = OpenAIProvider(
            LLMConfig(
                provider="openai",
                api_key=openai_config["api_key"],
                base_url=openai_config["base_url"],
                model=openai_config["model"],
            )
        )

        messages = [{"role": "user", "content": "Count from 1 to 3, separated by spaces."}]

        chunks = []
        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        # 验证至少收到了一些chunks
        assert len(chunks) > 0

        # 验证有text类型的chunk
        text_chunks = [c for c in chunks if c.type == "text"]
        assert len(text_chunks) > 0

        # 验证有done类型的chunk
        done_chunks = [c for c in chunks if c.type == "done"]
        assert len(done_chunks) > 0

    @requires_real_api
    @pytest.mark.asyncio
    async def test_chat_with_temperature(self, openai_config):
        """测试temperature参数"""
        provider = OpenAIProvider(
            LLMConfig(
                provider="openai",
                api_key=openai_config["api_key"],
                base_url=openai_config["base_url"],
                model=openai_config["model"],
                temperature=0.0,  # 低temperature，输出更确定
            )
        )

        messages = [
            {"role": "user", "content": "What is the capital of France? Answer in one word."}
        ]

        response = await provider.chat(messages)

        # 验证响应
        assert response.content is not None
        assert "Paris" in response.content or "paris" in response.content
