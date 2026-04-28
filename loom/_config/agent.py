"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .generation import GenerationConfig
from .heartbeat import HeartbeatConfig
from .knowledge import KnowledgeSource
from .memory import MemoryConfig
from .model import ModelRef
from .orchestration import OrchestrationConfig
from .policy import PolicyConfig
from .runtime import RuntimeConfig
from .safety import SafetyRule
from .schedule import ScheduledJob
from .tools import Toolset, ToolSpec


@dataclass(slots=True)
class AgentConfig:
    """Top-level public configuration for one Loom agent."""

    model: ModelRef
    instructions: str = ""
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    tools: list[ToolSpec | Toolset] = field(default_factory=list)
    capabilities: list[Any] = field(default_factory=list)
    policy: PolicyConfig | None = None
    memory: MemoryConfig | None = None
    heartbeat: HeartbeatConfig | None = None
    runtime: RuntimeConfig | None = None
    orchestration: OrchestrationConfig | None = None
    schedule: list[ScheduledJob] = field(default_factory=list)
    safety_rules: list[SafetyRule] | None = None
    knowledge: list[KnowledgeSource] = field(default_factory=list)
