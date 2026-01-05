"""
豆包 (Doubao) LLM Provider

基于 OpenAI 兼容 API 实现。
"""

import os
from loom.llm.providers.openai_compatible import OpenAICompatibleProvider


class DoubaoProvider(OpenAICompatibleProvider):
    """
    豆包 (字节跳动) Provider

    使用方式：
        provider = DoubaoProvider(
            api_key="...",
            model="doubao-pro-32k"
        )
    """

    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    DEFAULT_MODEL = "doubao-pro-32k"
    API_KEY_ENV_VAR = "DOUBAO_API_KEY"
    PROVIDER_NAME = "Doubao (豆包)"

    def __init__(self, **kwargs):
        if 'api_key' not in kwargs:
            kwargs['api_key'] = os.getenv(self.API_KEY_ENV_VAR)

        super().__init__(**kwargs)
