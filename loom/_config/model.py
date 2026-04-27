"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ModelRef:
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
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="anthropic",
            name=name,
            api_base=api_base,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def openai(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        organization: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="openai",
            name=name,
            api_base=api_base,
            organization=organization,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def gemini(
        cls,
        name: str,
        *,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="gemini",
            name=name,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def qwen(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="qwen",
            name=name,
            api_base=api_base,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def deepseek(
        cls,
        name: str = "deepseek-chat",
        *,
        api_base: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        """DeepSeek provider.  Use ``deepseek-chat`` for tool calling and
        ``deepseek-reasoner`` for chain-of-thought reasoning (R1)."""
        return cls(
            provider="deepseek",
            name=name,
            api_base=api_base,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def minimax(
        cls,
        name: str = "MiniMax-Text-01",
        *,
        api_base: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        """MiniMax provider.  Supports ``MiniMax-Text-01``, ``MiniMax-M1``
        (thinking), and ``abab6.5s-chat``."""
        return cls(
            provider="minimax",
            name=name,
            api_base=api_base,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def ollama(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="ollama",
            name=name,
            api_base=api_base,
            extensions=dict(extensions or {}),
        )

    @property
    def identifier(self) -> str:
        return f"{self.provider}:{self.name}"
