"""
Context Sources - 上下文源实现

提供各种上下文源的具体实现。
"""

from loom.context.sources.agent import AgentOutputSource
from loom.context.sources.inherited import InheritedSource
from loom.context.sources.memory import (
    L1WindowSource,
    L2WorkingSource,
    L3PersistentSource,
)
from loom.context.sources.prompt import PromptSource
from loom.context.sources.rag import RAGKnowledgeSource
from loom.context.sources.shared_pool import SharedPoolSource
from loom.context.sources.skill import SkillSource
from loom.context.sources.tool import ToolSource
from loom.context.sources.user import UserInputSource

__all__ = [
    # Memory Sources (3-layer)
    "L1WindowSource",
    "L2WorkingSource",
    "L3PersistentSource",
    # Knowledge Source
    "RAGKnowledgeSource",
    # Context Sources
    "UserInputSource",
    "AgentOutputSource",
    "PromptSource",
    "ToolSource",
    "SkillSource",
    # Shared Memory
    "SharedPoolSource",
    # Other
    "InheritedSource",
]
