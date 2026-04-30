"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Model:
    """Stable model reference for one provider-backed model."""

    provider: str
    name: str
    api_base: str | None = None
    organization: str | None = None
    api_key_env: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def anthropic(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> Model:
        resolved_api_base = _resolve_api_base(api_base, base_url)
        return cls(
            provider="anthropic",
            name=name,
            api_base=resolved_api_base,
            api_key_env=api_key_env,
            extensions=_provider_extensions(
                extensions,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            ),
        )

    @classmethod
    def openai(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        base_url: str | None = None,
        organization: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> Model:
        resolved_api_base = _resolve_api_base(api_base, base_url)
        return cls(
            provider="openai",
            name=name,
            api_base=resolved_api_base,
            organization=organization,
            api_key_env=api_key_env,
            extensions=_provider_extensions(
                extensions,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            ),
        )

    @classmethod
    def gemini(
        cls,
        name: str,
        *,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> Model:
        return cls(
            provider="gemini",
            name=name,
            api_key_env=api_key_env,
            extensions=_provider_extensions(
                extensions,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            ),
        )

    @classmethod
    def qwen(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> Model:
        resolved_api_base = _resolve_api_base(api_base, base_url)
        return cls(
            provider="qwen",
            name=name,
            api_base=resolved_api_base,
            api_key_env=api_key_env,
            extensions=_provider_extensions(
                extensions,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            ),
        )

    @classmethod
    def deepseek(
        cls,
        name: str = "deepseek-chat",
        *,
        api_base: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> Model:
        """DeepSeek provider.  Use ``deepseek-chat`` for tool calling and
        ``deepseek-reasoner`` for chain-of-thought reasoning (R1)."""
        resolved_api_base = _resolve_api_base(api_base, base_url)
        return cls(
            provider="deepseek",
            name=name,
            api_base=resolved_api_base,
            api_key_env=api_key_env,
            extensions=_provider_extensions(
                extensions,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            ),
        )

    @classmethod
    def minimax(
        cls,
        name: str = "MiniMax-Text-01",
        *,
        api_base: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> Model:
        """MiniMax provider.  Supports ``MiniMax-Text-01``, ``MiniMax-M1``
        (thinking), and ``abab6.5s-chat``."""
        resolved_api_base = _resolve_api_base(api_base, base_url)
        return cls(
            provider="minimax",
            name=name,
            api_base=resolved_api_base,
            api_key_env=api_key_env,
            extensions=_provider_extensions(
                extensions,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            ),
        )

    @classmethod
    def ollama(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> Model:
        resolved_api_base = _resolve_api_base(api_base, base_url)
        return cls(
            provider="ollama",
            name=name,
            api_base=resolved_api_base,
            extensions=_provider_extensions(
                extensions,
                timeout=timeout,
                max_retries=max_retries,
            ),
        )

    @property
    def identifier(self) -> str:
        return f"{self.provider}:{self.name}"


def _resolve_api_base(api_base: str | None, base_url: str | None) -> str | None:
    if api_base is not None and base_url is not None and api_base != base_url:
        raise TypeError("Use either api_base or base_url, not both")
    return api_base if api_base is not None else base_url


def _provider_extensions(
    extensions: dict[str, Any] | None,
    *,
    api_key: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> dict[str, Any]:
    result = dict(extensions or {})
    if api_key is not None:
        result["api_key"] = api_key
    if timeout is not None:
        result["timeout"] = timeout
    if max_retries is not None:
        result["max_retries"] = max_retries
    return result
