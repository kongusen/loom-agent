"""Configuration models for Loom runtime"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM configuration"""
    model: str = "gpt-4-turbo"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 120


@dataclass
class ToolConfig:
    """Tool permission configuration"""
    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)
    require_approval: list[str] = field(default_factory=list)


@dataclass
class PolicyConfig:
    """Policy configuration"""
    policy_id: str = "default"
    approval_timeout: int = 600
    max_depth: int = 3
    enable_verification: bool = False


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str = "default"
    llm: LLMConfig = field(default_factory=LLMConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    system_prompt: str = ""
