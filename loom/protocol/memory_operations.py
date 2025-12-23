"""
Protocols for Metabolic Memory Operations.
"""

from typing import Any, Dict, List, Protocol, runtime_checkable

@runtime_checkable
class MemoryValidator(Protocol):
    """
    Protocol for assessing the value/importance of a memory entry.
    """
    async def validate(self, content: Any) -> float:
        """
        Return an importance score between 0.0 and 1.0.
        """
        ...

@runtime_checkable
class ContextSanitizer(Protocol):
    """
    Protocol for cleaning and summarizing context.
    """
    async def sanitize(self, context: str, target_token_limit: int) -> str:
        """
        Reduce context to meet token limit while preserving meaning.
        """
        ...

@runtime_checkable
class ProjectStateObject(Protocol):
    """
    Protocol for the Project State Object (PSO).
    Maintains a structured representation of the current project state.
    """
    async def update(self, events: List[Dict[str, Any]]) -> None:
        """
        Update the state based on a list of recent events or memory entries.
        """
        ...
        
    async def snapshot(self) -> Dict[str, Any]:
        """
        Return the current state as a dictionary.
        """
        ...

    def to_markdown(self) -> str:
        """
        Return the state as a Markdown string (for LLM context).
        """
        ...
