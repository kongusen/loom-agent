"""Tokenizer implementations — estimation and tiktoken-based."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import Tokenizer


class EstimatorTokenizer:
    """Fast char-ratio estimation (no dependencies)."""

    def __init__(self, chars_per_token: int = 4, cache_size: int = 1000) -> None:
        self._ratio = chars_per_token
        self._cache_size = cache_size

    @lru_cache(maxsize=1000)
    def count(self, text: str) -> int:
        """P2: LRU 缓存 - 自动淘汰."""
        return len(text) // self._ratio + 1

    def count_incremental(self, base_text: str, delta_text: str) -> int:
        """P2: 增量计算 - 避免重复."""
        base_tokens = self.count(base_text)
        delta_tokens = self.count(delta_text)
        return base_tokens + delta_tokens

    def truncate(self, text: str, max_tokens: int) -> str:
        max_chars = max_tokens * self._ratio
        return text[:max_chars] if len(text) > max_chars else text


class TiktokenTokenizer:
    """Accurate tiktoken-based counting (requires tiktoken)."""

    def __init__(self, model: str = "gpt-4") -> None:
        try:
            import tiktoken
            self._enc = tiktoken.encoding_for_model(model)
        except ImportError:
            raise ImportError("tiktoken not installed. Run: pip install tiktoken")

    def count(self, text: str) -> int:
        return len(self._enc.encode(text))

    def truncate(self, text: str, max_tokens: int) -> str:
        tokens = self._enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self._enc.decode(tokens[:max_tokens])


def create_tokenizer(provider: str = "estimator", model: str = "gpt-4") -> Tokenizer:
    """Factory for tokenizer instances."""
    if provider == "tiktoken":
        return TiktokenTokenizer(model)
    return EstimatorTokenizer()
