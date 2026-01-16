"""
Custom LLM Provider

通用的自定义 Provider，支持任意 OpenAI 兼容的 API。
"""

import os

from loom.config.llm import ConnectionConfig, GenerationConfig, LLMConfig
from loom.llm.providers.openai_compatible import OpenAICompatibleProvider


class CustomProvider(OpenAICompatibleProvider):
    """
    Custom Provider - 通用自定义 Provider

    支持任意 OpenAI 兼容的 API endpoint。

    使用方式：
        provider = CustomProvider(
            model="custom-model-name",
            base_url="https://api.example.com/v1",
            api_key="your-api-key"
        )
    """

    DEFAULT_BASE_URL = "http://localhost:1234/v1"
    DEFAULT_MODEL = "local-model"
    API_KEY_ENV_VAR: str | None = None
    PROVIDER_NAME = "Custom"

    def __init__(
        self,
        config: LLMConfig | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ):
        """
        初始化 Custom Provider

        Args:
            model: 模型名称（必需）
            base_url: API endpoint（必需）
            api_key: API key（可选，取决于服务器配置）
            temperature: 温度参数
            max_tokens: 最大token数
        """
        if not base_url:
            raise ValueError(
                "CustomProvider requires base_url. "
                "Example: base_url='https://api.example.com/v1'"
            )

        if config is None:
            config = LLMConfig()

            # API key 可选
            if self.API_KEY_ENV_VAR:
                api_key = api_key or os.getenv(self.API_KEY_ENV_VAR) or "custom"
            else:
                api_key = api_key or "custom"

            config.connection = ConnectionConfig(
                api_key=api_key,
                base_url=base_url
            )

            config.generation = GenerationConfig(
                model=model or self.DEFAULT_MODEL,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens
            )

        super().__init__(config=config, **kwargs)
