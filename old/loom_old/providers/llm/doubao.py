"""
豆包 (Doubao) LLM Provider

基于 OpenAI 兼容 API 实现。
"""

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


class DoubaoProvider(OpenAICompatibleProvider):
    """
    豆包 (字节跳动) Provider

    使用方式：
        provider = DoubaoProvider(
            api_key="...",
            model="doubao-pro-32k"
        )

        # 或从环境变量读取
        provider = DoubaoProvider(model="doubao-lite-4k")
    """

    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    DEFAULT_MODEL = "doubao-pro-32k"
    API_KEY_ENV_VAR = "DOUBAO_API_KEY"
    PROVIDER_NAME = "Doubao (豆包)"
