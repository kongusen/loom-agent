from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from loom.core.types import Message


class BaseCompressor(ABC):
    """上下文压缩策略接口。"""

    @abstractmethod
    async def compress(self, messages: List[Message]) -> List[Message]:
        raise NotImplementedError

    @abstractmethod
    def should_compress(self, token_count: int, max_tokens: int) -> bool:
        raise NotImplementedError

