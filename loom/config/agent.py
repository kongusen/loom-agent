"""Agent configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str | None = None
    system_prompt: str = "You are a helpful assistant."
    max_steps: int = 10
    temperature: float = 0.7
    max_tokens: int = 4096
    token_budget: int = 128_000
    stream: bool = True
    tool_context: dict[str, Any] = field(default_factory=dict)
