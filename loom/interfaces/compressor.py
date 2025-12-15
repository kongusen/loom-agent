from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from loom.core.message import Message  # Unified Message architecture


class BaseCompressor(ABC):
    """
    Context compression interface

    简化版本 v0.1.6：只返回压缩后的消息列表，不返回元数据。

    这样做的原因：
    - 简化接口
    - 压缩元数据在大多数场景下不需要
    - 如果需要元数据，可以通过自定义 compressor 的属性获取
    """

    @abstractmethod
    async def compress(
        self, messages: List[Message]
    ) -> List[Message]:
        """
        压缩消息列表

        Args:
            messages: 要压缩的消息列表

        Returns:
            压缩后的消息列表

        Example:
            compressed = await compressor.compress(history)
        """
        raise NotImplementedError

