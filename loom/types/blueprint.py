"""Agent blueprint types for the Blueprint Forge system."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class AgentBlueprint:
    """A template for creating specialized agents.

    Blueprints are designed by LLM and evolve based on reward signals,
    similar to skill-creator's iterative description optimization.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    system_prompt: str = ""
    domain: str = "general"
    domain_scores: dict[str, float] = field(default_factory=dict)
    tools_filter: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    generation: int = 1
    parent_id: str | None = None
    # Performance tracking
    total_spawns: int = 0
    total_tasks: int = 0
    avg_reward: float = 0.0
    reward_history: list[float] = field(default_factory=list)
