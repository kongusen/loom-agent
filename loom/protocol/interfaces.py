"""
Core Protocols for Loom Framework.
Adhering to the "Protocol-First" design principle using typing.Protocol.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, AsyncIterator, Union

from loom.protocol.cloudevents import CloudEvent

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

    async def call(self, target_node: str, data: Dict[str, Any]) -> Any:
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
    async def add(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a memory entry."""
        ...

    async def get_context(self, task: str = "") -> str:
        """Get full context formatted for the LLM."""
        ...
        
    async def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent memory entries."""
        ...
        
    async def clear(self) -> None:
        """Clear memory."""
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
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Any: # Returns LLMResponse compatible object
        ...

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        ...

# ----------------------------------------------------------------------
# Infra Protocols
# ----------------------------------------------------------------------

@runtime_checkable
class TransportProtocol(Protocol):
    """
    Protocol for Event Transport (Pub/Sub).
    """
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def publish(self, topic: str, event: CloudEvent) -> None: ...
    async def subscribe(self, topic: str, handler: Any) -> None: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    """
    Protocol for the Universal Event Bus.
    """
    async def publish(self, event: CloudEvent) -> None: ...
    async def subscribe(self, topic: str, handler: Any) -> None: ...
