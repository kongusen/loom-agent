from typing import List, Optional
from abc import ABC, abstractmethod
from loom.core.message import Message

class BaseMemory(ABC):
    """
    Base class for Memory Systems.

    Philosophy:
    - Memory is NOT a Runnable (it is a state manager)
    - Provides add/retrieve/clear interfaces
    """

    @abstractmethod
    async def add_message(self, message: Message) -> None:
        """Add a message to memory."""
        ...

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        **kwargs
    ) -> List[Message]:
        """
        Semantically retrieve relevant messages.

        Args:
            query: Query text
            top_k: Number of results

        Returns:
            List of relevant messages
        """
        ...

    @abstractmethod
    async def get_recent(self, limit: int = 10) -> List[Message]:
        """Get recent messages."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear memory."""
        ...
