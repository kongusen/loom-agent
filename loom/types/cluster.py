"""Cluster / self-organizing agent types."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

AgentNodeStatus = Literal["idle", "busy", "splitting", "dying"]
Priority = Literal["low", "normal", "high", "critical"]


@dataclass
class CapabilityProfile:
    scores: dict[str, float] = field(default_factory=dict)
    tools: list[str] = field(default_factory=list)
    total_tasks: int = 0
    success_rate: float = 0.0


@dataclass
class RewardSignal:
    quality: float = 0.0
    efficiency: float = 0.0
    reliability: float = 0.0


@dataclass
class RewardRecord:
    task_id: str = ""
    reward: float = 0.0
    domain: str = ""
    token_cost: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    parent_id: str | None = None
    depth: int = 0
    capabilities: CapabilityProfile = field(default_factory=CapabilityProfile)
    reward_history: list[RewardRecord] = field(default_factory=list)
    status: AgentNodeStatus = "idle"
    load: float = 0.0
    agent: Any = None
    last_active_at: float = field(default_factory=time.time)
    consecutive_losses: int = 0


@dataclass
class TaskAd:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    description: str = ""
    estimated_complexity: float = 0.5
    priority: Priority = "normal"
    required_tools: list[str] = field(default_factory=list)
    token_budget: int = 4096


@dataclass
class Bid:
    agent_id: str = ""
    task_id: str = ""
    score: float = 0.0
    breakdown: dict[str, float] = field(default_factory=dict)
    estimated_tokens: int = 0


@dataclass
class SubTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    domain: str = ""
    dependencies: list[str] = field(default_factory=list)
    estimated_complexity: float = 0.3


@dataclass
class TaskResultMetadata:
    confidence: float | None = None
    key_findings: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class TaskResult:
    task_id: str
    agent_id: str
    content: str
    success: bool
    token_cost: int = 0
    error_count: int = 0
    duration_ms: int = 0
    metadata: TaskResultMetadata | None = None


@dataclass
class TaskSpec:
    task: TaskAd | None = None
    objective: str = ""
    output_format: str | None = None
    boundaries: str | None = None
    tool_guidance: str | None = None
    domain_hints: list[str] = field(default_factory=list)


@dataclass
class ComplexityEstimate:
    score: float = 0.5
    domains: list[str] = field(default_factory=list)
    reasoning: str | None = None
    method: Literal["heuristic", "llm"] = "heuristic"


@dataclass
class MitosisContext:
    parent_task_spec: TaskSpec | None = None
    subtask: SubTask | None = None
    parent_tools: list[str] = field(default_factory=list)
    context: Any = None  # ContextOrchestrator
    memory: Any = None   # MemoryManager


@dataclass
class Skill:
    name: str = ""
    description: str = ""
    instructions: str = ""
    activation_level: Literal["always", "conditional", "manual"] = "conditional"
    priority: float = 0.5
    trigger: Any = None   # SkillTrigger
    tools: list[Any] = field(default_factory=list)
