"""Qwen provider (Alibaba Cloud DashScope, OpenAI-compatible)."""

from .openai import OpenAIProvider

_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class QwenProvider(OpenAIProvider):
    """Qwen provider via Alibaba Cloud DashScope OpenAI-compatible API.

    Args:
        api_key: DashScope API key (https://dashscope.console.aliyun.com/).
        model: Defaults to ``qwen-plus``. Other options: ``qwen-turbo``,
               ``qwen-max``, ``qwen2.5-72b-instruct``, etc.
        base_url: Override the DashScope endpoint (e.g. for a proxy).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = _DASHSCOPE_BASE_URL,
    ):
        super().__init__(api_key=api_key, base_url=base_url)
