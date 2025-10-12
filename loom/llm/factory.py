"""LLM 工厂模式

根据配置自动创建对应的 LLM 实例，支持：
- 自动注册与发现
- 统一的创建接口
- 类型安全
"""

from __future__ import annotations

from typing import Dict, Type, Any, cast
from .config import LLMConfig, LLMProvider
from loom.interfaces.llm import BaseLLM


class LLMFactory:
    """LLM 工厂

    负责根据配置创建对应的 LLM 实例。
    """

    _registry: Dict[LLMProvider, Type[BaseLLM]] = {}

    @classmethod
    def register(cls, provider: LLMProvider, llm_class: Type[BaseLLM]):
        cls._registry[provider] = llm_class

    @classmethod
    def create(cls, config: LLMConfig) -> BaseLLM:
        """根据配置创建 LLM 实例。优先调用 from_config，其次按 provider 适配构造。"""
        cls._ensure_registered()

        if config.provider not in cls._registry:
            raise ValueError(
                f"Unsupported LLM provider: {config.provider}. Available: {list(cls._registry.keys())}"
            )

        llm_class = cls._registry[config.provider]

        # 优先使用 classmethod from_config(config)
        from_config = getattr(llm_class, "from_config", None)
        if callable(from_config):
            return cast(BaseLLM, from_config(config))

        # 无 from_config，按 provider 适配常用构造参数
        if config.provider in (LLMProvider.OPENAI, LLMProvider.AZURE_OPENAI, LLMProvider.CUSTOM):
            kwargs: dict[str, Any] = {
                "model": config.model_name,
                "temperature": config.temperature,
            }
            if config.max_tokens is not None:
                kwargs["max_tokens"] = config.max_tokens
            if config.base_url is not None:
                kwargs["base_url"] = config.base_url
            if config.api_key is not None:
                kwargs["api_key"] = config.api_key
            kwargs.update(config.extra_params)
            return llm_class(**kwargs)  # type: ignore[arg-type]

        # 其他提供商暂不内置适配
        raise ValueError(f"Provider {config.provider} has no default constructor mapping")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> BaseLLM:
        config = LLMConfig.from_dict(config_dict)
        return cls.create(config)

    # 便捷创建方法
    @classmethod
    def create_openai(
        cls,
        api_key: str,
        model: str = "gpt-4",
        **kwargs
    ) -> BaseLLM:
        config = LLMConfig.openai(api_key=api_key, model=model, **kwargs)
        return cls.create(config)

    # 私有：延迟注册可用实现
    @classmethod
    def _ensure_registered(cls):
        if cls._registry:
            return

        # 注册内置实现（按实际存在的实现）
        try:
            from loom.builtin.llms.openai import OpenAILLM
            cls.register(LLMProvider.OPENAI, OpenAILLM)
            # 兼容自定义/代理/azure: 复用 OpenAI 客户端风格
            cls.register(LLMProvider.AZURE_OPENAI, OpenAILLM)
            cls.register(LLMProvider.CUSTOM, OpenAILLM)
        except Exception:
            pass

        try:
            from loom.builtin.llms.mock import MockLLM
            # 仅用于测试时手动注册（无 provider 枚举映射）
        except Exception:
            pass

        try:
            from loom.builtin.llms.rule import RuleLLM
            # 规则引擎型 LLM（不绑定 provider）
        except Exception:
            pass

    @classmethod
    def list_available_providers(cls) -> list[str]:
        cls._ensure_registered()
        return [provider.value for provider in cls._registry.keys()]

