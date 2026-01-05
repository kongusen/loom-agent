"""
Custom LLM Provider

通用的自定义 Provider，支持任意 OpenAI 兼容的 API。
"""

import os
from typing import Optional
from loom.llm.providers.openai_compatible import OpenAICompatibleProvider
from loom.config.llm import LLMConfig, ConnectionConfig, GenerationConfig


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

    DEFAULT_BASE_URL = None  # 必须由用户指定
    DEFAULT_MODEL = "gpt-3.5-turbo"  # 默认模型名
    API_KEY_ENV_VAR = "CUSTOM_LLM_API_KEY"
    PROVIDER_NAME = "Custom"

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
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
            api_key = api_key or os.getenv(self.API_KEY_ENV_VAR) or "custom"

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
