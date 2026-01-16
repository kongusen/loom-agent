"""
Unified Token Counter Service

Consolidates token counting logic from context.py and compression.py
to eliminate duplication and provide consistent token counting across
the memory and context systems.
"""

from typing import Any, Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore

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

    _instance: Optional["TokenCounter"] = None
    _initialized = False

    def __new__(cls, _encoding: str = "cl100k_base") -> "TokenCounter":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, encoding: str = "cl100k_base"):
        """Initialize token counter (only once due to singleton)."""
        if self._initialized:
            return

        self.encoding_name = encoding
        self.encoder: Any | None = None
        if tiktoken is None:
            print("tiktoken not available, falling back to simple token estimation")
            self.encoder = None
        else:
            try:
                self.encoder = tiktoken.get_encoding(encoding)
            except Exception as e:
                print(f"Failed to load tiktoken encoding '{encoding}': {e}")
                print("Falling back to simple token estimation")
                self.encoder = None

        # Instance-level cache to avoid memory leaks from lru_cache on methods
        self._cache: dict[str, int] = {}
        self._cache_maxsize = 2048
        self._cache_hits = 0
        self._cache_misses = 0

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

    def count_message(self, message: dict[str, str]) -> int:
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

    def count_memory_units(self, units: list[MemoryUnit]) -> int:
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

    def count_messages(self, messages: list[dict[str, str]]) -> int:
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

    def _encode_cached(self, text: str) -> int:
        """
        Encode text with caching.

        Uses instance-level cache to avoid re-encoding identical strings.
        This is important for repeated content like system prompts.

        Args:
            text: Text to encode

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        # Check cache first
        if text in self._cache:
            self._cache_hits += 1
            return self._cache[text]

        # Cache miss
        self._cache_misses += 1

        # Encode and cache result
        if self.encoder:
            try:
                tokens = self.encoder.encode(text)
                result = len(tokens)
            except Exception as e:
                print(f"Error encoding text with tiktoken: {e}")
                result = self.estimate_tokens(text)
        else:
            result = self.estimate_tokens(text)

        # Add to cache with LRU eviction
        if len(self._cache) >= self._cache_maxsize:
            # Remove oldest entry (first key)
            self._cache.pop(next(iter(self._cache)))
        self._cache[text] = result

        return result

    # ============================================================================
    # Statistics and Cache Management
    # ============================================================================

    def get_cache_info(self) -> dict[str, int]:
        """
        Get cache statistics for the internal encoding cache.

        Returns:
            Dictionary with hits, misses, currsize, maxsize
        """
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "currsize": len(self._cache),
            "maxsize": self._cache_maxsize,
        }

    def clear_cache(self):
        """Clear the encoding cache."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


# Module-level convenience access
_counter: TokenCounter | None = None


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
