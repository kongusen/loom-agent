"""
Hierarchical Memory Implementation
"""

import time
from typing import List, Dict, Any, Optional

from loom.interfaces.memory import MemoryInterface, MemoryEntry

class HierarchicalMemory(MemoryInterface):
    """
    A simplified 4-tier memory system.
    
    Tiers:
    1. Ephemeral: Tool outputs (not implemented separate storage in this MVP, just tagged)
    2. Working: Recent N items.
    3. Session: Full conversation history.
    4. Long-term: (Stub) Vector interactions.
    """
    
    def __init__(self, session_limit: int = 100, working_limit: int = 5):
        self.session_limit = session_limit
        self.working_limit = working_limit
        
        self._session: List[MemoryEntry] = []
        # working memory is a dynamic view or separate buffer? 
        # In legacy design, it was promoted. Here, let's treat it as "Recent Window" logic for start.
        
    async def add(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add to session memory."""
        # print(f"[DEBUG Memory] Adding {role}: {content[:20]}...")
        metadata = metadata or {}
        tier = metadata.get("tier", "session")
        
        entry = MemoryEntry(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata,
            tier=tier
        )
        
        self._session.append(entry)
        
        # Enforce limits
        if len(self._session) > self.session_limit:
            self._session.pop(0) # Simple FIFO
            
    async def get_context(self, task: str = "") -> str:
        """
        Construct a context string for the Agent.
        
        Format:
        --- Long Term Memory ---
        (Stub)
        
        --- Session History ---
        User: ...
        Assistant: ...
        """
        # Long term stub
        long_term = ""
        
        # Working/Session view
        # We perform a simple sliding window for now suitable for LLM Context Window
        # or return full session if it fits.
        
        history_str = []
        for entry in self._session:
             history_str.append(f"{entry.role.capitalize()}: {entry.content}")
             
        return "\n".join(history_str)

    async def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent raw messages for LLM API."""
        messages = []
        for entry in self._session[-limit:]:
            msg = {"role": entry.role, "content": entry.content}

            # Include tool_calls for assistant messages
            if entry.role == "assistant" and "tool_calls" in entry.metadata:
                msg["tool_calls"] = entry.metadata["tool_calls"]

            # Include tool_call_id for tool messages
            if entry.role == "tool" and "tool_call_id" in entry.metadata:
                msg["tool_call_id"] = entry.metadata["tool_call_id"]
                if "tool_name" in entry.metadata:
                    msg["name"] = entry.metadata["tool_name"]

            messages.append(msg)
        return messages

    async def clear(self) -> None:
        self._session.clear()
