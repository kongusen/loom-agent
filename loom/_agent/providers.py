"""Provider resolution and provider readiness helpers."""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

from ..config import AgentConfig, ModelRef
from ..providers.base import CompletionParams, LLMProvider
from ..runtime import RunContext
from .normalization import _is_provider_health_check_enabled

logger = logging.getLogger(__name__)


class ProviderMixin:
    if TYPE_CHECKING:
        config: AgentConfig
        _provider: LLMProvider | None
        _provider_resolved: bool
        _provider_from_resolver: bool
        _provider_validated: bool

    def _get_provider(self) -> LLMProvider | None:
        if not self._provider_resolved:
            public_agent_module = sys.modules.get("loom.agent")
            resolver = getattr(public_agent_module, "_resolve_provider", _resolve_provider)
            self._provider = resolver(self.config.model)
            self._provider_resolved = True
            self._provider_from_resolver = self._provider is not None
            self._provider_validated = False
        return self._provider

    async def _ensure_provider_ready(self, provider: LLMProvider) -> bool:
        if not self._provider_from_resolver:
            return True
        if self._provider_validated:
            return True
        if not _is_provider_health_check_enabled(self.config.runtime):
            self._provider_validated = True
            return True

        try:
            await provider.complete_response(
                [{"role": "user", "content": "ping"}],
                CompletionParams(
                    model=self.config.model.name,
                    max_tokens=1,
                    temperature=0.0,
                ),
            )
        except Exception as exc:
            logger.warning(
                "Provider health check failed for %s: %s",
                self.config.model.identifier,
                exc,
            )
            return False

        self._provider_validated = True
        return True

    def _local_output(self, prompt: str, context: RunContext | None) -> str:
        if context is not None:
            payload = context.to_payload()
            if payload:
                return f"Completed goal: {prompt} with context keys {sorted(payload.keys())}"
        return f"Completed goal: {prompt}"


def _resolve_provider(model: ModelRef) -> LLMProvider | None:
    provider_name = model.provider.lower()

    try:
        if provider_name == "anthropic":
            api_key = os.getenv(model.api_key_env or "ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(f"{model.api_key_env or 'ANTHROPIC_API_KEY'} not set")
            from ..providers.anthropic import AnthropicProvider

            return AnthropicProvider(api_key=api_key, base_url=model.api_base)

        if provider_name == "openai":
            api_key = os.getenv(model.api_key_env or "OPENAI_API_KEY")
            if not api_key:
                raise ValueError(f"{model.api_key_env or 'OPENAI_API_KEY'} not set")
            from ..providers.openai import OpenAIProvider

            return OpenAIProvider(
                api_key=api_key,
                base_url=model.api_base or os.getenv("OPENAI_BASE_URL"),
                organization=model.organization,
            )

        if provider_name == "gemini":
            api_env = model.api_key_env
            api_key = (
                os.getenv(api_env)
                if api_env
                else os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            )
            if not api_key:
                raise ValueError(f"{api_env or 'GEMINI_API_KEY or GOOGLE_API_KEY'} not set")
            from ..providers.gemini import GeminiProvider

            return GeminiProvider(api_key=api_key)

        if provider_name == "qwen":
            api_key = os.getenv(model.api_key_env or "DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError(f"{model.api_key_env or 'DASHSCOPE_API_KEY'} not set")
            from ..providers.qwen import QwenProvider

            return QwenProvider(
                api_key=api_key,
                **({"base_url": model.api_base} if model.api_base else {}),
            )

        if provider_name == "deepseek":
            api_key = os.getenv(model.api_key_env or "DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError(f"{model.api_key_env or 'DEEPSEEK_API_KEY'} not set")
            from ..providers.deepseek import DeepSeekProvider

            return DeepSeekProvider(
                api_key=api_key,
                **({"base_url": model.api_base} if model.api_base else {}),
            )

        if provider_name == "minimax":
            api_key = os.getenv(model.api_key_env or "MINIMAX_API_KEY")
            if not api_key:
                raise ValueError(f"{model.api_key_env or 'MINIMAX_API_KEY'} not set")
            from ..providers.minimax import MiniMaxProvider

            return MiniMaxProvider(
                api_key=api_key,
                **({"base_url": model.api_base} if model.api_base else {}),
            )

        if provider_name == "ollama":
            from ..providers.ollama import OllamaProvider

            return OllamaProvider(
                base_url=model.api_base or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
            )

        raise ValueError(f"Unknown provider: {provider_name}")
    except Exception as exc:
        logger.warning("Failed to initialize provider %s: %s", provider_name, exc)
        return None
