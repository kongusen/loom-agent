"""
OpenAI Compatible Provider Base Class

为兼容 OpenAI API 格式的供应商提供通用实现。
适用于：DeepSeek、智谱AI、Kimi、通义千问、豆包、Ollama 等。

特性：
1. 使用 LLMConfig 统一配置管理
2. 直接继承 OpenAIProvider
3. 子类只需定义类属性提供默认值
"""

from typing import Any

from loom.config.llm import LLMConfig
from loom.providers.llm.openai import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """
    OpenAI 兼容 Provider 基类

    继承自 OpenAIProvider，使用子类定义的默认值填充配置。

    子类定义方式：
        class DeepSeekProvider(OpenAICompatibleProvider):
            DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
            DEFAULT_MODEL = "deepseek-chat"
            PROVIDER_NAME = "DeepSeek"

    使用方式：
        from loom.config import LLMConfig

        config = LLMConfig(
            provider="deepseek",
            api_key="sk-...",  # 必须提供
            # model 和 base_url 可选，会使用子类的默认值
        )

        provider = DeepSeekProvider(config)
    """

    # 子类需要覆盖这些类属性
    DEFAULT_BASE_URL: str | None = None
    DEFAULT_MODEL: str | None = None
    PROVIDER_NAME: str = "OpenAI Compatible"

    def __init__(self, config: LLMConfig, **kwargs: Any):
        """
        初始化兼容 Provider

        Args:
            config: LLM 配置对象
            **kwargs: 额外参数传递给 AsyncOpenAI 客户端

        Raises:
            ValueError: 如果 api_key 未在配置中提供
        """
        # 创建配置副本，填充默认值
        config_dict = config.model_dump()

        # 使用子类定义的默认值填充缺失的字段
        if not config_dict.get("model") and self.DEFAULT_MODEL:
            config_dict["model"] = self.DEFAULT_MODEL

        if not config_dict.get("base_url") and self.DEFAULT_BASE_URL:
            config_dict["base_url"] = self.DEFAULT_BASE_URL

        # 创建新的配置对象
        final_config = LLMConfig(**config_dict)

        # 调用父类初始化
        super().__init__(final_config, **kwargs)
