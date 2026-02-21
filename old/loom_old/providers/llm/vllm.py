"""
vLLM Provider

支持 vLLM 高性能推理引擎。
"""

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


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

    def __init__(self, **kwargs):
        """初始化 vLLM Provider"""
        # vLLM 可能不需要 API key，使用占位符
        if "api_key" not in kwargs:
            kwargs["api_key"] = kwargs.get("api_key") or "vllm"

        super().__init__(**kwargs)
