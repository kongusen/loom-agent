"""
DeepSeek LLM Provider

基于 OpenAI 兼容 API 实现。
"""

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """
    DeepSeek Provider

    使用方式：
        provider = DeepSeekProvider(
            api_key="sk-...",
            model="deepseek-chat"
        )

        # 或从环境变量读取
        provider = DeepSeekProvider(model="deepseek-chat")
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"
    API_KEY_ENV_VAR = "DEEPSEEK_API_KEY"
    PROVIDER_NAME = "DeepSeek"
