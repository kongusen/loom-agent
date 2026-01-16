"""
Ollama LLM Provider

支持本地运行的 Ollama 模型。
"""


from loom.config.llm import ConnectionConfig, GenerationConfig, LLMConfig
from loom.llm.providers.openai_compatible import OpenAICompatibleProvider


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
    API_KEY_ENV_VAR: str | None = None  # Ollama 不需要 API key
    PROVIDER_NAME = "Ollama"

    def __init__(
        self,
        config: LLMConfig | None = None,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ):
        """初始化 Ollama Provider"""
        if config is None:
            config = LLMConfig()

            config.connection = ConnectionConfig(
                api_key="ollama",  # Ollama 需要一个占位符
                base_url=base_url or self.DEFAULT_BASE_URL
            )

            config.generation = GenerationConfig(
                model=model or self.DEFAULT_MODEL,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens
            )

        super().__init__(config=config, **kwargs)
