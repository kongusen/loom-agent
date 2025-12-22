from typing import Any, Optional
from loom.builtin.llms.unified import UnifiedLLM

class OpenAILLM(UnifiedLLM):
    """OpenAI LLM - UnifiedLLM Wrapper"""
    def __init__(self, api_key: str, **kwargs: Any):
        super().__init__(api_key=api_key, provider="openai", **kwargs)

class DeepSeekLLM(UnifiedLLM):
    """DeepSeek LLM - UnifiedLLM Wrapper"""
    def __init__(self, api_key: str, **kwargs: Any):
        super().__init__(api_key=api_key, provider="deepseek", **kwargs)

class QwenLLM(UnifiedLLM):
    """Qwen LLM - UnifiedLLM Wrapper"""
    def __init__(self, api_key: str, **kwargs: Any):
        super().__init__(api_key=api_key, provider="qwen", **kwargs)

class KimiLLM(UnifiedLLM):
    """Kimi LLM - UnifiedLLM Wrapper"""
    def __init__(self, api_key: str, **kwargs: Any):
        super().__init__(api_key=api_key, provider="kimi", **kwargs)

class ZhipuLLM(UnifiedLLM):
    """Zhipu/GLM LLM - UnifiedLLM Wrapper"""
    def __init__(self, api_key: str, **kwargs: Any):
        super().__init__(api_key=api_key, provider="zhipu", **kwargs)

class DoubaoLLM(UnifiedLLM):
    """Doubao LLM - UnifiedLLM Wrapper"""
    def __init__(self, api_key: str, **kwargs: Any):
        super().__init__(api_key=api_key, provider="doubao", **kwargs)

class YiLLM(UnifiedLLM):
    """Yi LLM - UnifiedLLM Wrapper"""
    def __init__(self, api_key: str, **kwargs: Any):
        super().__init__(api_key=api_key, provider="yi", **kwargs)

class CustomLLM(UnifiedLLM):
    """Custom OpenAI-Compatible LLM Wrapper"""
    def __init__(self, api_key: str, base_url: str, **kwargs: Any):
        super().__init__(api_key=api_key, provider="custom", base_url=base_url, **kwargs)
