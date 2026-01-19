"""
GPU Stack Provider

支持 GPU Stack 集群管理平台。
"""

from loom.providers.llm.openai_compatible import OpenAICompatibleProvider


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

    def __init__(self, **kwargs):
        """初始化 GPU Stack Provider"""
        # GPU Stack 可能不需要 API key，使用占位符
        if "api_key" not in kwargs:
            kwargs["api_key"] = "gpustack"

        super().__init__(**kwargs)
