from __future__ import annotations

from typing import List, Optional

from loom.core.types import Message
from loom.interfaces.memory import BaseMemory


class InMemoryMemory(BaseMemory):
    def __init__(self) -> None:
        self._messages: List[Message] = []

    async def add_message(self, message: Message) -> None:
        self._messages.append(message)

    async def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        return self._messages[-limit:] if limit else list(self._messages)

    async def clear(self) -> None:
        self._messages.clear()

