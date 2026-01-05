"""
LoomMemory Storage Engine
"""
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime

from .types import (
    MemoryUnit, MemoryTier, MemoryType,
    MemoryQuery, ContextProjection
)
from loom.config.memory import MemoryConfig
from .factory import create_vector_store, create_embedding_provider
from .vector_store import VectorStoreProvider
from .embedding import EmbeddingProvider


class LoomMemory:
    """
    Tiered Memory Storage System.
    
    L1 (Raw IO): Circular buffer for recent raw interactions.
    L2 (Working): Task-specific working memory.
    L3 (Session): Session-scoped history.
    L4 (Global): Persistent global knowledge.
    """
    
    def __init__(
        self,
        node_id: str,
        max_l1_size: int = 50,
        config: Optional[MemoryConfig] = None
    ):
        self.node_id = node_id
        self.config = config or MemoryConfig()
        # Use passed max_l1_size parameter, not config default
        self.max_l1_size = max_l1_size

        # Tiered Storage
        self._l1_buffer: List[MemoryUnit] = []           # Circular buffer
        self._l2_working: List[MemoryUnit] = []          # Working memory list
        self._l3_session: Dict[str, List[MemoryUnit]] = defaultdict(list) # By session_id
        self._l4_global: List[MemoryUnit] = []           # Mock for VectorDB

        # Indexes
        self._id_index: Dict[str, MemoryUnit] = {}
        self._type_index: Dict[MemoryType, List[str]] = defaultdict(list)

        # Vector Store & Embedding (Pluggable)
        self.vector_store: Optional[VectorStoreProvider] = create_vector_store(
            self.config.vector_store
        )
        self.embedding_provider: Optional[EmbeddingProvider] = create_embedding_provider(
            self.config.embedding
        ) if self.vector_store else None
    
    async def add(self, unit: MemoryUnit) -> str:
        """Add a memory unit to the appropriate tier."""
        # Ensure source_node is set
        unit.source_node = unit.source_node or self.node_id

        # Add to Tier
        if unit.tier == MemoryTier.L1_RAW_IO:
            self._l1_buffer.append(unit)
            if len(self._l1_buffer) > self.max_l1_size:
                self._evict_from_l1()

        elif unit.tier == MemoryTier.L2_WORKING:
            self._l2_working.append(unit)

        elif unit.tier == MemoryTier.L3_SESSION:
            session_id = unit.metadata.get("session_id", "default")
            self._l3_session[session_id].append(unit)

        elif unit.tier == MemoryTier.L4_GLOBAL:
            self._l4_global.append(unit)

            # Auto-vectorize L4 content if enabled
            if self.config.auto_vectorize_l4 and self.vector_store and self.embedding_provider:
                await self._vectorize_unit(unit)

        # Update Indexes
        self._id_index[unit.id] = unit
        self._type_index[unit.type].append(unit.id)

        return unit.id
    
    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        """Retrieve a memory unit by ID."""
        return self._id_index.get(unit_id)
    
    async def query(self, q: MemoryQuery) -> List[MemoryUnit]:
        """
        Query memory units based on criteria.
        """
        results = []

        # 1. Collect from requested tiers
        target_tiers = q.tiers or [
            MemoryTier.L1_RAW_IO,
            MemoryTier.L2_WORKING,
            MemoryTier.L3_SESSION,
            MemoryTier.L4_GLOBAL
        ]
        
        for tier in target_tiers:
            if tier == MemoryTier.L1_RAW_IO:
                results.extend(self._l1_buffer)
            elif tier == MemoryTier.L2_WORKING:
                results.extend(self._l2_working)
            elif tier == MemoryTier.L3_SESSION:
                for session_units in self._l3_session.values():
                    results.extend(session_units)
            elif tier == MemoryTier.L4_GLOBAL:
                results.extend(self._l4_global)
        
        # 2. Filter by Type
        if q.types:
            results = [u for u in results if u.type in q.types]
        
        # 3. Filter by Node ID
        if q.node_ids:
            results = [u for u in results if u.source_node in q.node_ids]
        
        # 4. Filter by Time
        if q.since:
            results = [u for u in results if u.created_at >= q.since]
        if q.until:
            results = [u for u in results if u.created_at <= q.until]
        
        # 5. Semantic Search (L4 Only for MVP)
        if q.query_text and MemoryTier.L4_GLOBAL in target_tiers:
            # Only perform semantic search on L4 items within the result set
            l4_candidates = [u for u in results if u.tier == MemoryTier.L4_GLOBAL]
            others = [u for u in results if u.tier != MemoryTier.L4_GLOBAL]

            scored_l4 = await self._semantic_search(q.query_text, l4_candidates, q.top_k)
            # For now, just append top K L4 matches to others.
            # Ideally, we might want to filter L4 to ONLY top K.
            # Strategy: If semantic search is requested, we PRIORITIZE semantic matches.
            results = others + scored_l4
        
        # 6. Sort
        reverse = q.descending
        # Dynamic getattr for sort key
        results.sort(
            key=lambda u: getattr(u, q.sort_by, u.created_at),
            reverse=reverse
        )
        
        return results
    
    def promote_to_l4(self, unit_id: str):
        """Promote a memory unit to L4 Global persistence."""
        unit = self.get(unit_id)
        if not unit:
            return
        
        # Remove from current tier if necessary (e.g. L2)
        if unit.tier == MemoryTier.L2_WORKING:
            if unit in self._l2_working:
                self._l2_working.remove(unit)
        
        # Update tier and add to L4
        unit.tier = MemoryTier.L4_GLOBAL
        if unit not in self._l4_global:
            self._l4_global.append(unit)
            
    def clear_working(self):
        """Clear L2 Working Memory."""
        for unit in self._l2_working:
             self._remove_from_index(unit)
        self._l2_working.clear()

    def _evict_from_l1(self):
        """
        Evict least important + least recently used item from L1 buffer.
        Uses importance-weighted LRU policy.
        """
        if not self._l1_buffer:
            return

        try:
            # Score = importance * recency_factor
            now = datetime.now()
            scored = []

            for unit in self._l1_buffer:
                age_seconds = (now - unit.created_at).total_seconds()
                # Recency factor decays over hours (1.0 at 0 hours, 0.5 at 1 hour, etc.)
                recency_factor = 1.0 / (1.0 + age_seconds / 3600)
                score = unit.importance * recency_factor
                scored.append((score, unit))

            # Sort by score (lowest first)
            scored.sort(key=lambda x: x[0])

            # Evict lowest scored item
            victim = scored[0][1]
            self._l1_buffer.remove(victim)
            self._remove_from_index(victim)
        except Exception as e:
            # Fallback to simple FIFO if scoring fails
            if self._l1_buffer:
                removed = self._l1_buffer.pop(0)
                self._remove_from_index(removed)

    def create_projection(
        self, 
        instruction: str,
        include_plan: bool = True,
        include_facts: bool = True
    ) -> ContextProjection:
        """Create a ContextProjection for a child node."""
        projection = ContextProjection(
            instruction=instruction,
            lineage=[self.node_id] # Start lineage with self
        )
        
        # Extract Parent Plan (Latest L2 Plan)
        if include_plan:
            plans = [u for u in self._l2_working if u.type == MemoryType.PLAN]
            if plans:
                # Use the latest plan as context
                projection.parent_plan = str(plans[-1].content)
        
        # Extract Relevant Facts (High importance L4)
        if include_facts:
            facts = [u for u in self._l4_global if u.importance > 0.7]
            projection.relevant_facts = facts[:5] # Limit to top 5
            
        return projection

    def get_statistics(self) -> Dict[str, Any]:
        """Get current memory statistics."""
        return {
            "l1_size": len(self._l1_buffer),
            "l2_size": len(self._l2_working),
            "l3_sessions": len(self._l3_session),
            "l4_size": len(self._l4_global),
            "total_units": len(self._id_index),
            "types": {
                t.value: len(ids) 
                for t, ids in self._type_index.items()
            }
        }

    def _remove_from_index(self, unit: MemoryUnit):
        """Helper to remove unit from indexes."""
        if unit.id in self._id_index:
            del self._id_index[unit.id]
        if unit.id in self._type_index[unit.type]:
            self._type_index[unit.type].remove(unit.id)

    async def _semantic_search(
        self,
        query: str,
        candidates: List[MemoryUnit],
        top_k: int
    ) -> List[MemoryUnit]:
        """
        Semantic Search using vector store if available, otherwise fallback to keyword matching.
        """
        # Use vector store if available
        if self.vector_store and self.embedding_provider:
            try:
                # Generate query embedding
                query_embedding = await self.embedding_provider.embed_text(query)

                # Search vector store
                results = await self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=top_k
                )

                # Map results back to MemoryUnits
                matched_units = []
                for result in results:
                    unit = self.get(result.id)
                    if unit and unit in candidates:
                        matched_units.append(unit)

                return matched_units
            except Exception as e:
                # Fallback to keyword matching on error
                pass

        # Fallback: Simple keyword matching
        scored = []
        query_lower = query.lower()

        for unit in candidates:
            score = 0.0
            content_str = str(unit.content).lower()

            if query_lower in content_str:
                score = 1.0

            final_score = score + (unit.importance * 0.1)
            scored.append((final_score, unit))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [unit for _, unit in scored[:top_k]]

    async def _vectorize_unit(self, unit: MemoryUnit):
        """
        Generate and store embedding for a memory unit.
        """
        if not self.vector_store or not self.embedding_provider:
            return

        try:
            # Generate embedding
            text = str(unit.content)
            embedding = await self.embedding_provider.embed_text(text)

            # Store in vector database
            await self.vector_store.add(
                id=unit.id,
                text=text,
                embedding=embedding,
                metadata={
                    "tier": unit.tier.name,
                    "type": unit.type.value,
                    "importance": unit.importance,
                    "source_node": unit.source_node
                }
            )

            # Store embedding in unit for future use
            unit.embedding = embedding
        except Exception as e:
            # Log error but don't fail the add operation
            pass
