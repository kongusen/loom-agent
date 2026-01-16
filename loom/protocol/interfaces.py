"""
Core Protocols for Loom Framework.
Adhering to the "Protocol-First" design principle using typing.Protocol.
"""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from loom.protocol.cloudevents import CloudEvent

if TYPE_CHECKING:
    from loom.llm.interface import StreamChunk

# ----------------------------------------------------------------------
# Node Protocol
# ----------------------------------------------------------------------

@runtime_checkable
class NodeProtocol(Protocol):
    """
    Protocol for any Node in the Loom Fractal System.
    """
    node_id: str
    source_uri: str

    async def process(self, event: CloudEvent) -> Any:
        """
        Process an incoming event and return a result.
        """
        ...

    async def call(self, target_node: str, data: dict[str, Any]) -> Any:
        """
        Send a request to another node and await the response.
        """
        ...

# ----------------------------------------------------------------------
# Memory Protocol
# ----------------------------------------------------------------------

@runtime_checkable
class MemoryStrategy(Protocol):
    """
    Protocol for Memory interactions.
    """
    async def add(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a memory entry."""
        ...

    async def get_context(self, task: str = "") -> str:
        """Get full context formatted for the LLM."""
        ...

    async def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent memory entries."""
        ...

    async def clear(self) -> None:
        """Clear memory."""
        ...


@runtime_checkable
class ReflectiveMemoryStrategy(MemoryStrategy, Protocol):
    """
    Extended Protocol for Memory with Reflection capabilities.

    ADDED: Reflection methods for metabolic memory management.
    Implementations that support reflection should implement this protocol.

    This follows Protocol-First design - not all memories need reflection,
    but those that do should implement these methods consistently.
    """

    def should_reflect(self, threshold: int = 20) -> bool:
        """
        Check if memory should be reflected/consolidated.

        Args:
            threshold: Number of entries that trigger reflection

        Returns:
            True if reflection should be performed
        """
        ...

    def get_reflection_candidates(self, count: int = 10) -> list[Any]:
        """
        Get memory entries to be reflected/summarized.

        Args:
            count: Number of entries to retrieve for reflection

        Returns:
            List of memory entries (implementation-specific format)
        """
        ...

    async def consolidate(self, summary: str, remove_count: int = 10) -> None:
        """
        Consolidate memories by replacing old entries with summary.

        Args:
            summary: The summarized/reflected knowledge
            remove_count: Number of old entries to remove

        This is the "metabolic" operation - converting detailed memories
        into compact knowledge representations.
        """
        ...

# ----------------------------------------------------------------------
# LLM Protocol
# ----------------------------------------------------------------------

# We need the LLMResponse type, but we can't easily import it if it's in the interface file
# without creating circular deps if that interface file imports this protocol file.
# For now, we will use Any or assume the structure matches.
# Ideally, data models should be in `loom.protocol.types` or similar,
# but we'll stick to `Any` or Dict for the strict Protocol definition to avoid tight coupling,
# OR we rely on structural subtyping.
# But let's try to be precise if possible.

@runtime_checkable
class LLMProviderProtocol(Protocol):
    """
    Protocol for LLM Providers.
    """
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None
    ) -> Any: # Returns LLMResponse compatible object
        ...

    async def stream_chat(
        self,
        _messages: list[dict[str, Any]],
        _tools: list[dict[str, Any]] | None = None
    ) -> AsyncGenerator["StreamChunk", None]:
        # Stub to indicate this is an async generator
        if False:
            yield  # type: ignore[unreachable]
        raise NotImplementedError

# ----------------------------------------------------------------------
# Infra Protocols
# ----------------------------------------------------------------------

@runtime_checkable
class TransportProtocol(Protocol):
    """
    Protocol for Event Transport (Pub/Sub).

    FIXED: Added unsubscribe() to prevent memory leaks.
    Handlers must be unsubscribed when no longer needed.
    """
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def publish(self, topic: str, event: CloudEvent) -> None: ...
    async def subscribe(self, topic: str, handler: Any) -> None: ...
    async def unsubscribe(self, topic: str, handler: Any) -> None: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    """
    Protocol for the Universal Event Bus.
    """
    async def publish(self, event: CloudEvent) -> None: ...
    async def subscribe(self, topic: str, handler: Any) -> None: ...
