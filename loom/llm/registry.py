"""模型能力注册表

维护各个 LLM 提供商和模型的能力信息，用于能力检测与查询。
"""

from __future__ import annotations

from typing import Dict
from .config import LLMCapabilities, LLMProvider


class ModelRegistry:
    OPENAI_MODELS: Dict[str, LLMCapabilities] = {
        "gpt-4": LLMCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
            supports_json_mode=True,
            supports_system_message=True,
            max_tokens=8192,
            context_window=8192,
        ),
        "gpt-4-turbo": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_json_mode=True,
            supports_system_message=True,
            max_tokens=4096,
            context_window=128000,
        ),
        "gpt-4o": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_json_mode=True,
            supports_system_message=True,
            max_tokens=16384,
            context_window=128000,
        ),
        "gpt-4o-mini": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_json_mode=True,
            supports_system_message=True,
            max_tokens=16384,
            context_window=128000,
        ),
        "gpt-3.5-turbo": LLMCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
            supports_json_mode=True,
            supports_system_message=True,
            max_tokens=4096,
            context_window=16385,
        ),
    }

    ANTHROPIC_MODELS: Dict[str, LLMCapabilities] = {
        "claude-3-5-sonnet-20241022": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_json_mode=False,
            supports_system_message=True,
            max_tokens=8192,
            context_window=200000,
        ),
        "claude-3-sonnet-20240229": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_json_mode=False,
            supports_system_message=True,
            max_tokens=4096,
            context_window=200000,
        ),
    }

    GOOGLE_MODELS: Dict[str, LLMCapabilities] = {
        "gemini-pro": LLMCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
            supports_json_mode=False,
            supports_system_message=True,
            max_tokens=8192,
            context_window=32760,
        ),
        "gemini-1.5-pro": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            supports_streaming=True,
            supports_json_mode=False,
            supports_system_message=True,
            max_tokens=8192,
            context_window=1000000,
        ),
    }

    COHERE_MODELS: Dict[str, LLMCapabilities] = {
        "command-r-plus": LLMCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
            supports_json_mode=False,
            supports_system_message=True,
            max_tokens=4096,
            context_window=128000,
        ),
        "command-r": LLMCapabilities(
            supports_tools=True,
            supports_vision=False,
            supports_streaming=True,
            supports_json_mode=False,
            supports_system_message=True,
            max_tokens=4096,
            context_window=128000,
        ),
    }

    DEFAULT_CAPABILITIES = LLMCapabilities(
        supports_tools=False,
        supports_vision=False,
        supports_streaming=True,
        supports_json_mode=False,
        supports_system_message=True,
        max_tokens=4096,
        context_window=8192,
    )

    @classmethod
    def get_capabilities(cls, provider: str, model_name: str) -> LLMCapabilities:
        provider = provider.lower()

        if provider == LLMProvider.OPENAI or provider == "azure_openai":
            return cls._get_with_fuzzy_match(cls.OPENAI_MODELS, model_name)
        elif provider == LLMProvider.ANTHROPIC:
            return cls._get_with_fuzzy_match(cls.ANTHROPIC_MODELS, model_name)
        elif provider == LLMProvider.GOOGLE:
            return cls._get_with_fuzzy_match(cls.GOOGLE_MODELS, model_name)
        elif provider == LLMProvider.COHERE:
            return cls._get_with_fuzzy_match(cls.COHERE_MODELS, model_name)
        elif provider == LLMProvider.OLLAMA:
            return LLMCapabilities(
                supports_tools=False,
                supports_vision=False,
                supports_streaming=True,
                supports_json_mode=False,
                supports_system_message=True,
                max_tokens=2048,
                context_window=8192,
            )
        else:
            return cls.DEFAULT_CAPABILITIES

    @classmethod
    def supports_tools(cls, provider: str, model_name: str) -> bool:
        return cls.get_capabilities(provider, model_name).supports_tools

    @classmethod
    def supports_vision(cls, provider: str, model_name: str) -> bool:
        return cls.get_capabilities(provider, model_name).supports_vision

    @classmethod
    def get_context_window(cls, provider: str, model_name: str) -> int:
        return cls.get_capabilities(provider, model_name).context_window

    @classmethod
    def register_model(
        cls,
        provider: str,
        model_name: str,
        capabilities: LLMCapabilities
    ):
        provider = provider.lower()
        if provider == LLMProvider.OPENAI:
            cls.OPENAI_MODELS[model_name] = capabilities
        elif provider == LLMProvider.ANTHROPIC:
            cls.ANTHROPIC_MODELS[model_name] = capabilities
        elif provider == LLMProvider.GOOGLE:
            cls.GOOGLE_MODELS[model_name] = capabilities
        elif provider == LLMProvider.COHERE:
            cls.COHERE_MODELS[model_name] = capabilities

    @classmethod
    def _get_with_fuzzy_match(
        cls,
        models: Dict[str, LLMCapabilities],
        model_name: str
    ) -> LLMCapabilities:
        if model_name in models:
            return models[model_name]
        model_name_lower = model_name.lower()
        for key, value in models.items():
            if model_name_lower in key.lower() or key.lower() in model_name_lower:
                return value
        return cls.DEFAULT_CAPABILITIES

