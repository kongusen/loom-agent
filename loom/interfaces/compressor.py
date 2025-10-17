from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple

from loom.core.types import Message, CompressionMetadata


class BaseCompressor(ABC):
    """Context compression interface (US2-compatible).

    Updated in v4.0.0 to return compression metadata alongside compressed messages.

    Migration Note:
        Old interface (v3.0.1):
            async def compress(self, messages) -> List[Message]

        New interface (v4.0.0):
            async def compress(self, messages) -> Tuple[List[Message], CompressionMetadata]

    For custom compressor implementations, update your compress() method to return
    a tuple: (compressed_messages, metadata).
    """

    @abstractmethod
    async def compress(
        self, messages: List[Message]
    ) -> Tuple[List[Message], CompressionMetadata]:
        """Compress messages and return metadata.

        Args:
            messages: List of messages to compress

        Returns:
            Tuple of (compressed_messages, compression_metadata)

        Example:
            compressed_msgs, metadata = await compressor.compress(history)
            print(f"Reduced tokens: {metadata.original_tokens} → {metadata.compressed_tokens}")
        """
        raise NotImplementedError

    @abstractmethod
    def should_compress(self, token_count: int, max_tokens: int) -> bool:
        """Check if compression should be triggered.

        Args:
            token_count: Current context token count
            max_tokens: Maximum allowed context tokens

        Returns:
            True if compression should be triggered (typically at 92% threshold)

        Example:
            if compressor.should_compress(15000, 16000):  # 93.75% usage
                compressed, metadata = await compressor.compress(history)
        """
        raise NotImplementedError

