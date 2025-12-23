"""
Metabolic Memory Core Implementation.
"""

import asyncio
from typing import Any, Dict, List, Optional
from loom.interfaces.memory import MemoryInterface, MemoryEntry
from loom.protocol.memory_operations import MemoryValidator, ProjectStateObject, ContextSanitizer
from loom.builtin.memory.validators import HeuristicValueAssessor
from loom.builtin.memory.pso import SimplePSO
from loom.builtin.memory.sanitizers import CompressiveSanitizer

class MetabolicMemory(MemoryInterface):
    """
    Advanced Memory System that 'metabolizes' information.
    1. Perceives (Validates importances)
    2. Maintains State (PSO)
    3. Consolidates (Compresses/Sanitizes)
    """
    
    def __init__(
        self, 
        validator: Optional[MemoryValidator] = None,
        pso: Optional[ProjectStateObject] = None,
        sanitizer: Optional[ContextSanitizer] = None
    ):
        self.validator = validator or HeuristicValueAssessor()
        self.pso = pso or SimplePSO()
        self.sanitizer = sanitizer or CompressiveSanitizer()
        
        self.short_term: List[MemoryEntry] = []
        self.limit = 10 # Short term limit before consolidation triggers
        
    async def add(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add entry with metabolic processing.
        """
        # 1. Perception / Validation
        importance = await self.validator.validate(content)
        
        # 2. Add to Short Term
        entry = MemoryEntry(
            role=role, 
            content=content, 
            metadata={**(metadata or {}), "importance": importance, "tier": "ephemeral"}
        )
        self.short_term.append(entry)
        
        # 3. Trigger Metabolism (Consolidation) if limit reached
        if len(self.short_term) > self.limit:
            await self.consolidate()

    async def get_context(self, task: str = "") -> str:
        """
        Construct context from PSO + Short Term.
        """
        pso_context = self.pso.to_markdown()
        
        # Get high importance short term or just recent
        recent_context = "\n".join([f"{e.role}: {e.content}" for e in self.short_term])
        
        return f"{pso_context}\n\n### Recent Activity\n{recent_context}"
        
    async def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [e.model_dump() for e in self.short_term[-limit:]]
        
    async def clear(self) -> None:
        self.short_term = []
        # PSO persists? Or clears? Usually PSO persists for the project lifetime.
        # But for 'clear memory' command, maybe we reset session.
        pass

    async def consolidate(self) -> None:
        """
        Metabolic Cycle:
        1. Update PSO with recent events.
        2. Compress short_term -> long_term (not impl here) or just drop low value.
        3. Keep only high value in short_term?
        """
        # 1. Update PSO
        # Convert entries to dicts for PSO
        events = [e.model_dump() for e in self.short_term]
        await self.pso.update(events)
        
        # 2. Prune Short Term
        # Keep only last N/2, or keep high score?
        # Simple FIFO for now, but in real metabolic, we'd keep high importance ones active longer.
        # Let's keep last 5.
        
        # If we wanted to "Santize" / Compress:
        # text_block = ...
        # compressed = await self.sanitizer.sanitize(text_block)
        # We might move compressed summary to a 'middle term' tier.
        
        keep_count = self.limit // 2
        self.short_term = self.short_term[-keep_count:]
