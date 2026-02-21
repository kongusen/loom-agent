"""
Kimi (Moonshot AI) LLM Provider

基于 OpenAI 兼容 API 实现。
"""

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


class KimiProvider(OpenAICompatibleProvider):
    """
    Kimi (月之暗面) Provider

    使用方式：
        provider = KimiProvider(
            api_key="sk-...",
            model="moonshot-v1-8k"
        )

        # 或从环境变量读取
        provider = KimiProvider(model="moonshot-v1-32k")
    """

    DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
    DEFAULT_MODEL = "moonshot-v1-8k"
    API_KEY_ENV_VAR = "MOONSHOT_API_KEY"
    PROVIDER_NAME = "Kimi (Moonshot AI)"
