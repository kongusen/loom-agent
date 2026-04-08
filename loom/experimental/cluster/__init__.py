"""Experimental filesystem-backed multi-agent primitives.

This package contains prototype coordination mechanisms that are intentionally
kept outside the main orchestration stack.
"""

from .event_bus import ClusterEvent, ClusterEventBus
from .fork import AgentFork, SubAgentConfig
from .shared_memory import SharedMemory

__all__ = [
    "AgentFork",
    "SubAgentConfig",
    "SharedMemory",
    "ClusterEvent",
    "ClusterEventBus",
]
