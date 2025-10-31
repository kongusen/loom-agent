"""Loom Unified API (v0.0.5)

Prefer `from loom import agent`.
For compatibility, `loom.api.loom_agent` aliases `loom.agent`.
"""

from ..agent import agent as loom_agent

__all__ = [
    "loom_agent",
]
