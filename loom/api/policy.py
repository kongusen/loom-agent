"""Policy set configuration"""

from dataclasses import dataclass, field


@dataclass
class PolicySet:
    """Policy set for agent behavior"""
    id: str
    name: str
    deny: list[str] = field(default_factory=list)
    require_approval: list[str] = field(default_factory=list)
    allow_quote_from: list[str] = field(default_factory=list)
    require_citation_for: list[str] = field(default_factory=list)
