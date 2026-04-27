"""State types for Agent execution"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LoopState(Enum):
    """L* execution states"""

    REASON = "reason"
    ACT = "act"
    OBSERVE = "observe"
    DELTA = "delta"
    GOAL_REACHED = "goal_reached"
    RENEW = "renew"
    DECOMPOSE = "decompose"


@dataclass
class EventSurface:
    """外部变化的认知界面"""

    pending_events: list[dict[str, Any]] = field(default_factory=list)
    active_risks: list[dict[str, Any]] = field(default_factory=list)
    recent_event_decisions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class KnowledgeSurface:
    """外部知识的证据界面"""

    active_questions: list[str] = field(default_factory=list)
    evidence_packs: list[dict[str, Any]] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


@dataclass
class Dashboard:
    """C_working - 永不压缩的工作记忆"""

    # 仪表盘指标
    rho: float = 0.0
    token_budget: int = 0
    goal_progress: str = ""
    error_count: int = 0
    depth: int = 0
    last_signal_ts: str = ""
    last_hb_ts: str = ""
    interrupt_requested: bool = False

    # 一等认知对象
    plan: list[str] = field(default_factory=list)
    event_surface: EventSurface = field(default_factory=EventSurface)
    knowledge_surface: KnowledgeSurface = field(default_factory=KnowledgeSurface)
    scratchpad: str = ""
