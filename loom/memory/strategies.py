"""
Observation Curation Strategies
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from .types import MemoryUnit, MemoryTier, MemoryType, MemoryQuery
from loom.config.memory import CurationConfig
# Avoid circular import by using ForwardRef or TYPE_CHECKING if necessary
# But here strategies depends on core types, core depends on types.
# Core LoomMemory is needed for type hint but we can use Any or TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import LoomMemory


class CurationStrategy(ABC):
    """Abstract Base Class for Curation Strategies."""

    @abstractmethod
    async def curate(
        self,
        memory: "LoomMemory",
        config: CurationConfig,
        task_context: Optional[str] = None
    ) -> List[MemoryUnit]:
        """
        Select memory units to include in the context.
        """
        pass


class AutoStrategy(CurationStrategy):
    """
    Auto Mode - Distance-based curation.
    
    Rules:
    - Self (distance=0): L2 Full + L1 Recent N
    - Parent (distance=1): L2 Plan + L3 Summaries
    - Grandparent+ (distance>=2): L4 Semantic Search
    """
    
    async def curate(
        self,
        memory: "LoomMemory",
        config: CurationConfig,
        task_context: Optional[str] = None
    ) -> List[MemoryUnit]:

        result = []

        # 1. Self - L2 Working Memory (Full)
        l2_query = MemoryQuery(
            tiers=[MemoryTier.L2_WORKING],
            node_ids=[memory.node_id]
        )
        result.extend(await memory.query(l2_query))

        # 2. Self - L1 Recent 10 (or configured limit)
        # Note: L1 is ephemeral, usually we only want the very last interaction exchange
        l1_query = MemoryQuery(
            tiers=[MemoryTier.L1_RAW_IO],
            node_ids=[memory.node_id],
            sort_by="created_at",
            descending=True
        )
        # Taking top 10 recent L1 items
        recent_l1 = await memory.query(l1_query)
        result.extend(recent_l1[:10])
        
        # 3. Parent - L3 Summaries (If distance >= 1)
        # Since we don't have explicit distance passed in curate(), we rely on config.focus_distance
        # Assumption: The current node is at 'focus_distance' 0 relative to itself.
        # But here 'focus_distance' in config implies "How far up we look"? 
        # Actually, in the plan, focus_distance meant "Focus on distance X". 
        # If focus_distance=0, we only care about self. 
        # If focus_distance=2, we care about self, parent, grandparent.
        
        if config.focus_distance >= 1:
            # We want plans/context from Parents (stored in L3 or L2 of parent, but locally available via projection?)
            # In current design, inherited memories are stored in this node's memory but maybe with different source?
            # Or we query the 'session' tier for broader context.
            l3_query = MemoryQuery(
                tiers=[MemoryTier.L3_SESSION],
                types=[MemoryType.PLAN, MemoryType.CONTEXT]
            )
            result.extend(await memory.query(l3_query))

        # 4. Grandparent+ - L4 Semantic Search (If distance >= 2)
        if config.focus_distance >= 2 and task_context:
            l4_query = MemoryQuery(
                tiers=[MemoryTier.L4_GLOBAL],
                query_text=task_context,
                top_k=5
            )
            result.extend(await memory.query(l4_query))

        return result


class SnippetsStrategy(CurationStrategy):
    """
    Snippets Mode - Progressive Disclosure.
    
    Rules:
    - Tools: Snippets only (Name/Desc)
    - Skills: Snippets of SKILL.md
    - Facts: Snippets
    - Recent Chat: Full
    """

    async def curate(
        self,
        memory: "LoomMemory",
        config: CurationConfig,
        task_context: Optional[str] = None
    ) -> List[MemoryUnit]:

        result = []

        # 1. Core Instructions (L2 PLAN) - Full
        plan_query = MemoryQuery(
            tiers=[MemoryTier.L2_WORKING],
            types=[MemoryType.PLAN]
        )
        result.extend(await memory.query(plan_query))

        # 2. Tools/Skills - Snippets
        if config.include_tools:
            tool_query = MemoryQuery(
                tiers=[MemoryTier.L2_WORKING, MemoryTier.L4_GLOBAL],
                types=[MemoryType.SKILL]
            )
            skills = await memory.query(tool_query)

            # Convert to snippets
            for skill in skills:
                snippet = MemoryUnit(
                    content=skill.to_snippet(),
                    tier=skill.tier,
                    type=MemoryType.CONTEXT,
                    metadata={"snippet_of": skill.id, "full_available": True, "name": skill.metadata.get("name")},
                    importance=skill.importance
                )
                result.append(snippet)

        # 3. Facts - High Relevance Snippets
        if config.include_facts and task_context:
            fact_query = MemoryQuery(
                tiers=[MemoryTier.L4_GLOBAL],
                types=[MemoryType.FACT],
                query_text=task_context,
                top_k=3
            )
            facts = await memory.query(fact_query)
            
            for fact in facts:
                snippet = MemoryUnit(
                    content=fact.to_snippet(),
                    tier=fact.tier,
                    type=MemoryType.CONTEXT,
                    metadata={"snippet_of": fact.id, "full_available": True},
                    importance=fact.importance
                )
                result.append(snippet)
        
        # 4. Recent Chat (L1) - Full
        recent_query = MemoryQuery(
            tiers=[MemoryTier.L1_RAW_IO],
            types=[MemoryType.MESSAGE],
            sort_by="created_at",
            descending=True
        )
        result.extend((await memory.query(recent_query))[:5])
        
        return result


class FocusedStrategy(CurationStrategy):
    """
    Focused Mode - Task-oriented curation across all tiers.
    """
    
    def curate(
        self,
        memory: "LoomMemory",
        config: CurationConfig,
        task_context: Optional[str] = None
    ) -> List[MemoryUnit]:
        
        if not task_context:
            # Fallback to Auto
            return AutoStrategy().curate(memory, config, task_context)
        
        # Semantic Search across L2, L3, L4
        query = MemoryQuery(
            tiers=[
                MemoryTier.L2_WORKING,
                MemoryTier.L3_SESSION,
                MemoryTier.L4_GLOBAL
            ],
            query_text=task_context,
            top_k=15
        )
        relevant = memory.query(query)
        
        # Ensure PLANs are prioritized
        plans = [u for u in relevant if u.type == MemoryType.PLAN]
        others = [u for u in relevant if u.type != MemoryType.PLAN]
        
        return plans + others


class StrategyFactory:
    """Factory for creating Curation Strategies."""
    
    _strategies = {
        "auto": AutoStrategy,
        "snippets": SnippetsStrategy,
        "focused": FocusedStrategy
    }
    
    
    @classmethod
    def create(cls, name: str) -> CurationStrategy:
        # Lazy import to avoid circular dependency
        from .system_strategies import System1Strategy, System2Strategy
        
        # Register system strategies dynamically if not present
        if "system1" not in cls._strategies:
            cls._strategies["system1"] = System1Strategy
        if "system2" not in cls._strategies:
            cls._strategies["system2"] = System2Strategy
            
        strategy_class = cls._strategies.get(name.lower())
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {name}")
        return strategy_class()
    
    @classmethod
    def register(cls, name: str, strategy_class: type):
        """Register a custom strategy."""
        cls._strategies[name.lower()] = strategy_class
