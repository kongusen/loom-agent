"""
DeepSeek LLM Provider

基于 OpenAI 兼容 API 实现。
"""

import os

from loom.llm.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """
    DeepSeek Provider

    使用方式：
        provider = DeepSeekProvider(
            api_key="sk-...",
            model="deepseek-chat"
        )
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"
    API_KEY_ENV_VAR = "DEEPSEEK_API_KEY"
    PROVIDER_NAME = "DeepSeek"

    def __init__(self, **kwargs):
        # 如果没有提供 api_key，尝试从环境变量读取
        if 'api_key' not in kwargs:
            kwargs['api_key'] = os.getenv(self.API_KEY_ENV_VAR)

        super().__init__(**kwargs)
