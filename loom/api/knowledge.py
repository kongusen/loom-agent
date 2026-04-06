"""Knowledge source registry"""

from dataclasses import dataclass, field
from typing import Optional
from .models import TrustTier


@dataclass
class KnowledgeSource:
    """External knowledge source"""
    id: str
    type: str  # filesystem, web, mcp, wiki
    scope: str  # project, tenant, global
    trust_tier: TrustTier
    allow_search: bool = True
    allow_quote: bool = True
    config: dict = field(default_factory=dict)


class KnowledgeRegistry:
    """Knowledge source registry"""

    def __init__(self):
        self.sources: dict[str, KnowledgeSource] = {}

    def register(self, source: KnowledgeSource) -> None:
        """Register knowledge source"""
        self.sources[source.id] = source

    def get(self, source_id: str) -> Optional[KnowledgeSource]:
        """Get knowledge source"""
        return self.sources.get(source_id)

    def list_by_scope(self, scope: str) -> list[KnowledgeSource]:
        """List sources by scope"""
        return [s for s in self.sources.values() if s.scope == scope]
