"""Loom Unified API (Version-agnostic)

This module provides the stable, version-agnostic API for Loom Agent.
Users should import from here instead of versioned modules.

Example:
    from loom.api import loom_agent
    from loom.builtin.llms import OpenAILLM

    agent = loom_agent(llm=OpenAILLM(model="gpt-4"), tools={})
"""

from .v0_0_3 import LoomAgent, loom_agent, unified_executor

__all__ = [
    "LoomAgent",
    "loom_agent",
    "unified_executor",
]
