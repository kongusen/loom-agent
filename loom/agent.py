"""Public Loom agent API.

This module is kept as the stable 0.x import path.  The implementation lives
under ``loom._agent`` so the runtime-facing pieces can evolve independently.
"""

from __future__ import annotations

from ._agent import Agent, tool
from ._agent.providers import _resolve_provider as _resolve_provider

__all__ = ["Agent", "tool"]
