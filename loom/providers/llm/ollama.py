"""
Ollama LLM Provider

支持本地运行的 Ollama 模型。
"""

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """
    Ollama Provider - 本地模型运行

    使用方式：
        # 默认配置（localhost:11434）
        provider = OllamaProvider(model="llama3.2")

        # 自定义地址
        provider = OllamaProvider(
            model="llama3.2",
            base_url="http://192.168.1.100:11434/v1"
        )
    """

    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    DEFAULT_MODEL = "llama3.2"
    API_KEY_ENV_VAR = None  # Ollama 不需要 API key
    PROVIDER_NAME = "Ollama"

    def __init__(self, **kwargs):
        """初始化 Ollama Provider"""
        # Ollama 需要一个占位符 API key
        if "api_key" not in kwargs:
            kwargs["api_key"] = "ollama"

        super().__init__(**kwargs)
