"""
vLLM Provider

支持 vLLM 高性能推理引擎。
"""

import os

from loom.config.llm import ConnectionConfig, GenerationConfig, LLMConfig
from loom.llm.providers.openai_compatible import OpenAICompatibleProvider


class VLLMProvider(OpenAICompatibleProvider):
    """
    vLLM Provider - 高性能推理引擎

    使用方式：
        provider = VLLMProvider(
            model="meta-llama/Llama-3.2-3B-Instruct",
            base_url="http://localhost:8000/v1",
            api_key="token-abc123"  # 可选
        )
    """

    DEFAULT_BASE_URL = "http://localhost:8000/v1"
    DEFAULT_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
    API_KEY_ENV_VAR = "VLLM_API_KEY"
    PROVIDER_NAME = "vLLM"

    def __init__(
        self,
        config: LLMConfig | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ):
        """初始化 vLLM Provider"""
        if config is None:
            config = LLMConfig()

            # vLLM 可能不需要 API key，使用占位符
            api_key = api_key or os.getenv(self.API_KEY_ENV_VAR) or "vllm"

            config.connection = ConnectionConfig(
                api_key=api_key,
                base_url=base_url or self.DEFAULT_BASE_URL
            )

            config.generation = GenerationConfig(
                model=model or self.DEFAULT_MODEL,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens
            )

        super().__init__(config=config, **kwargs)
