"""
System-Specific Context Strategies.
Defines how memory is curated for System 1 (Fast) vs System 2 (Slow).
"""

from typing import List, Optional

from loom.memory.strategies import CurationStrategy, CurationConfig, AutoStrategy
from loom.memory.core import LoomMemory
from loom.memory.types import MemoryUnit, MemoryTier, MemoryType, MemoryQuery


class System1Strategy(CurationStrategy):
    """
    System 1 Strategy: Minimal Context, Fast Retrieval.
    
    Characteristics:
    - Recent L1 messages (Short-term memory)
    - Cached L4 facts (High frequency)
    - Minimal L2 (Current instruction only)
    - Direct response focus (No heavy reasoning context)
    - Strict Token Budget (~500 tokens)
    """
    
    async def curate(
        self,
        memory: LoomMemory,
        config: CurationConfig,
        task_context: Optional[str] = None
    ) -> List[MemoryUnit]:

        result = []

        # 1. Recent L1 (Raw IO) - Very limited to keep it fast context
        # Just the last few turns
        l1_query = MemoryQuery(
            tiers=[MemoryTier.L1_RAW_IO],
            types=[MemoryType.MESSAGE],
            sort_by="created_at",
            descending=True
        )
        # Limit to last 5 messages
        l1_results = await memory.query(l1_query)
        result.extend(l1_results[:5])

        # 2. L2 (Working) - Current Plan only (if any)
        # System 1 doesn't need the full tool execution history usually
        l2_query = MemoryQuery(
            tiers=[MemoryTier.L2_WORKING],
            types=[MemoryType.PLAN]
        )
        result.extend(await memory.query(l2_query))

        # 3. L4 (Global) - Only high confidence/importance "cached" knowledge
        # Simulating "Cache" by sorting by access_count (if we had it) or importance
        if config.include_facts:
            l4_query = MemoryQuery(
                tiers=[MemoryTier.L4_GLOBAL],
                types=[MemoryType.FACT],
                sort_by="importance",
                descending=True
            )
            # Only top 3 "cached" facts to simulate instinct
            l4_results = await memory.query(l4_query)
            result.extend(l4_results[:3])

        return result


class System2Strategy(CurationStrategy):
    """
    System 2 Strategy: Comprehensive Context, Deep Reasoning.
    
    Characteristics:
    - Extensive L1 history
    - Full L2 Working Memory (Plans, Tool calls, Thoughts)
    - Relevant L3 Session history
    - L4 Semantic Search results
    - Large Token Budget (~8k+)
    """
    
    async def curate(
        self,
        memory: LoomMemory,
        config: CurationConfig,
        task_context: Optional[str] = None
    ) -> List[MemoryUnit]:

        # System 2 is basically "Auto" mode but potentially more exhaustive
        # We can reuse or extend AutoStrategy, but let's be explicit here.

        result = []

        # 1. Full L2 Working Memory (The Workspace)
        l2_query = MemoryQuery(
            tiers=[MemoryTier.L2_WORKING],
            node_ids=[memory.node_id]
        )
        result.extend(await memory.query(l2_query))

        # 2. Extensive L1 History
        l1_query = MemoryQuery(
            tiers=[MemoryTier.L1_RAW_IO],
            node_ids=[memory.node_id],
            sort_by="created_at",
            descending=True
        )
        # Deeper history for analysis (e.g., last 20)
        l1_results = await memory.query(l1_query)
        result.extend(l1_results[:20])

        # 3. Relevant L3 (Session)
        if config.focus_distance >= 1:
             l3_query = MemoryQuery(
                tiers=[MemoryTier.L3_SESSION],
                types=[MemoryType.PLAN, MemoryType.THOUGHT]
            )
             result.extend(await memory.query(l3_query))

        # 4. L4 Semantic Search (The Knowledge Base)
        # Only if we have a task context to search against
        if task_context and config.include_facts:
            l4_query = MemoryQuery(
                tiers=[MemoryTier.L4_GLOBAL],
                query_text=task_context,
                top_k=10 # Deeper search
            )
            result.extend(await memory.query(l4_query))

        return result
