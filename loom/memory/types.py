"""
LoomMemory Type Definitions
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
from datetime import datetime
import uuid


class MemoryTier(Enum):
    """
    Memory Tiers (L1-L4) representing the lifecycle and persistence of information.
    """
    L1_RAW_IO = 1      # Raw Input/Output (Ephemeral, buffer)
    L2_WORKING = 2     # Working Memory (Task-specific, scratchpad)
    L3_SESSION = 3     # Session History (Conversation, context)
    L4_GLOBAL = 4      # Global Knowledge (Persistent, semantic facts)


class MemoryType(Enum):
    """
    Types of memory content for categorization and filtering.
    """
    MESSAGE = "message"           # Chat messages (user/assistant)
    THOUGHT = "thought"           # Internal thoughts/monologue
    TOOL_CALL = "tool_call"       # Tool execution requests
    TOOL_RESULT = "tool_result"   # Tool execution results
    PLAN = "plan"                 # Plans or instructions
    FACT = "fact"                 # Extracted facts or knowledge
    SKILL = "skill"               # Skill/Tool definitions
    CONTEXT = "context"           # Context snippets/summaries
    SUMMARY = "summary"           # Context compression summary


class MemoryStatus(Enum):
    """
    Status of memory units for lifecycle management.
    """
    ACTIVE = "active"           # Currently active and accessible
    ARCHIVED = "archived"       # Archived but retrievable
    SUMMARIZED = "summarized"   # Compressed into summary
    EVICTED = "evicted"         # Removed from active memory


@dataclass
class MemoryUnit:
    """
    The fundamental unit of storage in LoomMemory.
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None  # The actual content (str, dict, etc.)
    tier: MemoryTier = MemoryTier.L2_WORKING
    type: MemoryType = MemoryType.MESSAGE
    
    # Source Tracking
    source_node: Optional[str] = None  # ID of the node that generated this
    parent_id: Optional[str] = None    # ID of parent memory (for causality chains)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Vector Embedding (for L4 Semantic Search)
    embedding: Optional[List[float]] = None
    
    # Importance Score (0.0 - 1.0) for Curation/Compression
    importance: float = 0.5

    # Lifecycle Status
    status: MemoryStatus = MemoryStatus.ACTIVE

    def to_message(self) -> Dict[str, str]:
        """Convert to LLM API message format."""
        if isinstance(self.content, dict) and "role" in self.content:
             return self.content
             
        if self.type == MemoryType.MESSAGE:
            # Assuming content is the text if it's not a dict, or we adhere to dict content for messages
            if isinstance(self.content, str):
                return {"role": "user", "content": self.content} # Default to user? Or should handle context contextually
            return self.content # Should be dict
        elif self.type == MemoryType.THOUGHT:
            return {"role": "assistant", "content": f"💭 {self.content}"}
        elif self.type == MemoryType.TOOL_CALL:
            # Handle both single tool call (dict) and multiple tool calls (list)
            if isinstance(self.content, list):
                # Multiple tool calls
                tool_names = [tc.get('name', 'unknown') if isinstance(tc, dict) else 'unknown' for tc in self.content]
                return {"role": "assistant", "content": f"🔧 Calling {', '.join(tool_names)}"}
            elif isinstance(self.content, dict):
                # Single tool call
                return {"role": "assistant", "content": f"🔧 Calling {self.content.get('name', 'unknown')}"}
            else:
                return {"role": "assistant", "content": f"🔧 Tool call: {str(self.content)}"}
        else:
            return {"role": "system", "content": str(self.content)}
    
    def to_snippet(self) -> str:
        """Convert to improved snippet/summary for progressive disclosure."""
        if self.type == MemoryType.SKILL:
            name = self.metadata.get('name', 'Unnamed')
            desc = self.metadata.get('description', '')[:50]
            return f"📚 {name}: {desc}..."
        elif self.type == MemoryType.PLAN:
            return f"🎯 Plan: {str(self.content)[:80]}..."
        else:
            content_str = str(self.content)[:60]
            return f"[{self.type.value}] {content_str}..."


@dataclass
class ContextProjection:
    """
    A projection of context passed from a Parent Node to a Child Node.
    This supports the fractal architecture by allowing selective inheritance.
    """
    
    # Mandatory: The core instruction/task for the child
    instruction: str
    
    # Selective Inheritance
    parent_plan: Optional[str] = None
    relevant_facts: List[MemoryUnit] = field(default_factory=list)
    tools_available: List[str] = field(default_factory=list)
    
    # Lineage Tracking
    lineage: List[str] = field(default_factory=list)  # [grandparent_id, parent_id]
    
    def to_memory_units(self) -> List[MemoryUnit]:
        """Convert projection data into initial MemoryUnits for the child."""
        units = []
        
        # 1. Instruction as L2 Working Memory
        units.append(MemoryUnit(
            content={"role": "system", "content": self.instruction},
            tier=MemoryTier.L2_WORKING,
            type=MemoryType.PLAN,
            importance=1.0,
            metadata={"projection_source": "instruction"}
        ))
        
        # 2. Parent Plan as L3 Context
        if self.parent_plan:
            units.append(MemoryUnit(
                content=self.parent_plan,
                tier=MemoryTier.L3_SESSION,
                type=MemoryType.CONTEXT,
                importance=0.7,
                metadata={"projection_source": "parent_plan"}
            ))
        
        # 3. Relevant Facts
        for fact in self.relevant_facts:
             # Clone fact but ensure it's treated as context/fact in new node
             units.append(MemoryUnit(
                 content=fact.content,
                 tier=fact.tier, # Keep original tier (likely L4)? Or move to L3/L4?
                 type=fact.type,
                 importance=fact.importance,
                 metadata={**fact.metadata, "projection_source": "fact"}
             ))
        
        return units


@dataclass 
class MemoryQuery:
    """
    Query parameters for retrieving memories.
    """
    
    # Filters
    tiers: List[MemoryTier] = field(default_factory=list)
    types: List[MemoryType] = field(default_factory=list)
    node_ids: List[str] = field(default_factory=list)
    
    # Semantic Search (L4)
    query_text: Optional[str] = None
    top_k: int = 5
    
    # Time Range
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    
    # Sorting
    sort_by: str = "created_at"  # created_at, importance, accessed_at
    descending: bool = True
