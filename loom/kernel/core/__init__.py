"""
Kernel Core - Layer 1: Foundation

Core execution engine components:
- UniversalEventBus: Event bus for pub/sub
- Dispatcher: Event dispatcher with interceptor support
- ToolExecutor: Parallel tool execution
- State management: Global and cognitive state
"""

from .bus import UniversalEventBus
from .dispatcher import Dispatcher
from .executor import ToolExecutor
from .state import StateStore as State
from .cognitive_state import CognitiveState, ProjectionOperator, Thought, ThoughtState

__all__ = [
    "UniversalEventBus",
    "Dispatcher",
    "ToolExecutor",
    "State",
    "CognitiveState",
    "ProjectionOperator",
    "Thought",
    "ThoughtState",
]
