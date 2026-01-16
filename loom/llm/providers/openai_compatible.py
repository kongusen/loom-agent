"""
OpenAI Compatible Provider Base Class

为兼容 OpenAI API 格式的供应商提供通用实现。
适用于：DeepSeek、智谱AI、Kimi、通义千问、豆包等。
"""

from loom.config.llm import ConnectionConfig, GenerationConfig, LLMConfig
from loom.llm.providers.openai import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """
    OpenAI 兼容 Provider 基类

    继承自 OpenAIProvider，只需配置不同的 base_url 和默认模型。
    """

    # 子类需要覆盖这些类属性
    DEFAULT_BASE_URL: str | None = None
    DEFAULT_MODEL: str | None = None
    API_KEY_ENV_VAR: str | None = None
    PROVIDER_NAME: str = "OpenAI Compatible"

    def __init__(
        self,
        config: LLMConfig | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ):
        """初始化兼容 Provider"""
        # 如果没有提供 config，创建默认配置
        if config is None:
            config = LLMConfig()

            # 使用子类定义的默认值
            config.connection = ConnectionConfig(
                api_key=api_key, base_url=base_url or self.DEFAULT_BASE_URL
            )

            config.generation = GenerationConfig(
                model=model or self.DEFAULT_MODEL or "gpt-3.5-turbo",
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens,
            )

        # 调用父类初始化
        super().__init__(config=config, **kwargs)
