"""Event types for Axiom 3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InformationEvent:
    """事件 e = ⟨id, sender, topic, payload, ΔH, priority, ts⟩"""

    id: str
    sender: str
    topic: str
    payload: Any
    delta_h: float  # 信息增益 ΔH(e)
    priority: int = 0
    ts: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
