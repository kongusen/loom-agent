"""
Custom LLM Provider

通用的自定义 Provider，支持任意 OpenAI 兼容的 API。
"""

from typing import Any

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


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
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        """
        初始化 Custom Provider

        Args:
            model: 模型名称
            base_url: API endpoint（推荐提供）
            api_key: API key（可选，取决于服务器配置）
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
        """
        # API key 可选，使用占位符
        if api_key is None:
            api_key = "custom"

        super().__init__(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
