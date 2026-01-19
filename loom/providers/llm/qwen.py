"""
通义千问 (Qwen) LLM Provider

基于 OpenAI 兼容 API 实现。
"""

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    """
    通义千问 Provider

    使用方式：
        provider = QwenProvider(
            api_key="sk-...",
            model="qwen-plus"
        )

        # 或从环境变量读取
        provider = QwenProvider(model="qwen-turbo")
    """

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = "qwen-plus"
    API_KEY_ENV_VAR = "DASHSCOPE_API_KEY"
    PROVIDER_NAME = "Qwen (通义千问)"
