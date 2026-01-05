"""
Unified Token Counter Service

Consolidates token counting logic from context.py and compression.py
to eliminate duplication and provide consistent token counting across
the memory and context systems.
"""

from typing import List, Dict, Optional, Union
from functools import lru_cache
import tiktoken

from loom.memory.types import MemoryUnit


class TokenCounter:
    """
    Singleton token counter service using tiktoken.

    Replaces:
    - context.py::ContextAssembler._count_tokens_msg
    - context.py::ContextAssembler._count_tokens_str
    - compression.py::MemoryCompressor._count_tokens

    Benefits:
    - Single source of truth for token counting
    - LRU cache to avoid recalculating tokens for identical content
    - Consistent encoding across memory and context systems
    - Support for multiple input types (strings, messages, units, lists)
    - Fallback when tiktoken is unavailable
    """

    _instance: Optional['TokenCounter'] = None
    _initialized = False

    def __new__(cls, encoding: str = "cl100k_base") -> 'TokenCounter':
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, encoding: str = "cl100k_base"):
        """Initialize token counter (only once due to singleton)."""
        if self._initialized:
            return

        self.encoding_name = encoding
        try:
            self.encoder = tiktoken.get_encoding(encoding)
        except Exception as e:
            print(f"Failed to load tiktoken encoding '{encoding}': {e}")
            print("Falling back to simple token estimation")
            self.encoder = None

        self._initialized = True

    def count_string(self, text: str) -> int:
        """
        Count tokens in a string.

        Replaces:
        - context.py::ContextAssembler._count_tokens_str

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        # Try to use cached encoding
        return self._encode_cached(text)

    def count_message(self, message: Dict[str, str]) -> int:
        """
        Count tokens in a message dictionary.

        Replaces:
        - context.py::ContextAssembler._count_tokens_msg

        Args:
            message: Message dict with 'content' key (and optionally 'role')

        Returns:
            Number of tokens
        """
        if not message:
            return 0

        # Extract content and encode
        content = str(message.get("content", ""))

        # Account for message formatting overhead
        # Role field adds minimal overhead (~2-3 tokens per message)
        role_tokens = 3

        return self._encode_cached(content) + role_tokens

    def count_memory_units(self, units: List[MemoryUnit]) -> int:
        """
        Count total tokens in a list of memory units.

        Replaces:
        - compression.py::MemoryCompressor._count_tokens

        Args:
            units: List of MemoryUnit objects

        Returns:
            Total number of tokens
        """
        if not units:
            return 0

        total = 0
        for unit in units:
            total += self.count_unit(unit)

        return total

    def count_unit(self, unit: MemoryUnit) -> int:
        """
        Count tokens in a single memory unit.

        Args:
            unit: MemoryUnit to count

        Returns:
            Number of tokens
        """
        if not unit or not unit.content:
            return 0

        content_str = str(unit.content)
        return self._encode_cached(content_str)

    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        """
        Count total tokens in a list of messages.

        Args:
            messages: List of message dicts

        Returns:
            Total number of tokens
        """
        if not messages:
            return 0

        total = 0
        for msg in messages:
            total += self.count_message(msg)

        return total

    # ============================================================================
    # Estimation Fallback
    # ============================================================================

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate tokens when tiktoken is unavailable.

        Rule of thumb: ~4 characters ≈ 1 token for English text

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)

    # ============================================================================
    # Internal Methods with Caching
    # ============================================================================

    @lru_cache(maxsize=2048)
    def _encode_cached(self, text: str) -> int:
        """
        Encode text with caching.

        Uses LRU cache to avoid re-encoding identical strings.
        This is important for repeated content like system prompts.

        Args:
            text: Text to encode

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self.encoder:
            try:
                tokens = self.encoder.encode(text)
                return len(tokens)
            except Exception as e:
                print(f"Error encoding text with tiktoken: {e}")
                return self.estimate_tokens(text)
        else:
            return self.estimate_tokens(text)

    # ============================================================================
    # Statistics and Cache Management
    # ============================================================================

    def get_cache_info(self) -> Dict[str, int]:
        """
        Get cache statistics for the internal encoding cache.

        Returns:
            Dictionary with hits, misses, currsize, maxsize
        """
        info = self._encode_cached.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "currsize": info.currsize,
            "maxsize": info.maxsize
        }

    def clear_cache(self):
        """Clear the encoding cache."""
        self._encode_cached.cache_clear()


# Module-level convenience access
_counter: Optional[TokenCounter] = None


def get_token_counter(encoding: str = "cl100k_base") -> TokenCounter:
    """
    Get the singleton TokenCounter instance.

    This is the recommended way to access the token counter across
    the application to ensure consistent token counting.

    Args:
        encoding: Tiktoken encoding name (default: cl100k_base for GPT-4)

    Returns:
        TokenCounter singleton instance
    """
    global _counter
    if _counter is None:
        _counter = TokenCounter(encoding)
    return _counter
