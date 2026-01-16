"""
智谱AI (GLM) LLM Provider

基于 OpenAI 兼容 API 实现。
"""

import os

from loom.llm.providers.openai_compatible import OpenAICompatibleProvider


class ZhipuProvider(OpenAICompatibleProvider):
    """
    智谱AI Provider

    使用方式：
        provider = ZhipuProvider(
            api_key="...",
            model="glm-4-plus"
        )
    """

    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_MODEL = "glm-4-plus"
    API_KEY_ENV_VAR = "ZHIPU_API_KEY"
    PROVIDER_NAME = "Zhipu AI"

    def __init__(self, **kwargs):
        if "api_key" not in kwargs:
            kwargs["api_key"] = os.getenv(self.API_KEY_ENV_VAR)

        super().__init__(**kwargs)
