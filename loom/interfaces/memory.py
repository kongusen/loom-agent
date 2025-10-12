from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from loom.core.types import Message


class BaseMemory(ABC):
    """对话/状态内存接口。"""

    @abstractmethod
    async def add_message(self, message: Message) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        raise NotImplementedError

    async def save(self, path: str) -> None:  # 可选
        return None

    async def load(self, path: str) -> None:  # 可选
        return None

