"""
Context Sources - 上下文源实现

提供各种上下文源的具体实现。
"""

from loom.context.sources.agent import AgentOutputSource
from loom.context.sources.inherited import InheritedSource
from loom.context.sources.memory import L1RecentSource, L2ImportantSource
from loom.context.sources.prompt import PromptSource
from loom.context.sources.rag import RAGKnowledgeSource
from loom.context.sources.semantic import L4SemanticSource
from loom.context.sources.skill import SkillSource
from loom.context.sources.tool import ToolSource
from loom.context.sources.user import UserInputSource

__all__ = [
    # Memory Sources
    "L1RecentSource",
    "L2ImportantSource",
    "L4SemanticSource",
    # Knowledge Source
    "RAGKnowledgeSource",
    # New Context Sources (7大来源)
    "UserInputSource",
    "AgentOutputSource",
    "PromptSource",
    "ToolSource",
    "SkillSource",
    # Other
    "InheritedSource",
]
