"""
智谱AI (GLM) LLM Provider

基于 OpenAI 兼容 API 实现。
"""

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


class ZhipuProvider(OpenAICompatibleProvider):
    """
    智谱AI Provider

    使用方式：
        provider = ZhipuProvider(
            api_key="...",
            model="glm-4-plus"
        )

        # 或从环境变量读取
        provider = ZhipuProvider(model="glm-4-flash")
    """

    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_MODEL = "glm-4-plus"
    API_KEY_ENV_VAR = "ZHIPU_API_KEY"
    PROVIDER_NAME = "Zhipu AI"
