"""
GPU Stack Provider

支持 GPU Stack 集群管理平台。
"""

import os

from loom.config.llm import ConnectionConfig, GenerationConfig, LLMConfig
from loom.llm.providers.openai_compatible import OpenAICompatibleProvider


class GPUStackProvider(OpenAICompatibleProvider):
    """
    GPU Stack Provider - GPU 集群管理

    使用方式：
        provider = GPUStackProvider(
            model="llama3.2",
            base_url="http://gpu-stack.example.com/v1",
            api_key="..."
        )
    """

    DEFAULT_BASE_URL = "http://localhost:8080/v1"
    DEFAULT_MODEL = "llama3.2"
    API_KEY_ENV_VAR = "GPUSTACK_API_KEY"
    PROVIDER_NAME = "GPU Stack"

    def __init__(
        self,
        config: LLMConfig | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ):
        """初始化 GPU Stack Provider"""
        if config is None:
            config = LLMConfig()

            api_key = api_key or os.getenv(self.API_KEY_ENV_VAR) or "gpustack"

            config.connection = ConnectionConfig(
                api_key=api_key, base_url=base_url or self.DEFAULT_BASE_URL
            )

            config.generation = GenerationConfig(
                model=model or self.DEFAULT_MODEL,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens,
            )

        super().__init__(config=config, **kwargs)
