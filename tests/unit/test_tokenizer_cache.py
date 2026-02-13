"""
TiktokenCounter LRU 缓存测试 + slots 数据类测试
"""

from unittest.mock import MagicMock

import pytest

from loom.context.block import ContextBlock
from loom.memory.tokenizer import TiktokenCounter

# ── TiktokenCounter Cache Tests ──


class TestTiktokenCache:
    def setup_method(self):
        try:
            self.counter = TiktokenCounter(model="gpt-4", cache_size=3)
        except Exception:
            pytest.skip("tiktoken not installed")

    def test_cache_returns_same_result(self):
        """缓存结果与直接计算一致"""
        text = "Hello, world!"
        first = self.counter.count(text)
        second = self.counter.count(text)
        assert first == second
        assert first > 0

    def test_cache_hit_avoids_encode(self):
        """第二次调用不触发 encode"""
        counter = TiktokenCounter(model="gpt-4", cache_size=16)
        text = "test string for cache"

        # First call populates cache
        result1 = counter.count(text)

        # Patch encode after first call
        original_encoding = counter._encoding
        mock_encode = MagicMock(return_value=[1, 2, 3])
        counter._encoding = MagicMock()
        counter._encoding.encode = mock_encode

        # Second call should use cache, not encode
        result2 = counter.count(text)
        mock_encode.assert_not_called()
        assert result2 == result1

        # Restore
        counter._encoding = original_encoding

    def test_cache_eviction(self):
        """cache_size=3 插入 4 条，最旧被淘汰"""
        self.counter.count("aaa")
        self.counter.count("bbb")
        self.counter.count("ccc")
        assert self.counter.cache_info["size"] == 3

        # Insert 4th, should evict "aaa"
        self.counter.count("ddd")
        assert self.counter.cache_info["size"] == 3
        assert "aaa" not in self.counter._cache
        assert "ddd" in self.counter._cache

    def test_cache_lru_ordering(self):
        """访问模式验证 LRU 淘汰顺序"""
        self.counter.count("aaa")
        self.counter.count("bbb")
        self.counter.count("ccc")

        # Access "aaa" again → moves to end
        self.counter.count("aaa")

        # Insert "ddd" → should evict "bbb" (oldest untouched)
        self.counter.count("ddd")
        assert "bbb" not in self.counter._cache
        assert "aaa" in self.counter._cache

    def test_clear_cache(self):
        """清空缓存"""
        self.counter.count("hello")
        assert self.counter.cache_info["size"] == 1
        self.counter.clear_cache()
        assert self.counter.cache_info["size"] == 0

    def test_cache_info(self):
        """返回正确的 size/max_size"""
        info = self.counter.cache_info
        assert info["size"] == 0
        assert info["max_size"] == 3

        self.counter.count("x")
        assert self.counter.cache_info["size"] == 1

    def test_empty_string_not_cached(self):
        """空字符串返回 0 不入缓存"""
        result = self.counter.count("")
        assert result == 0
        assert self.counter.cache_info["size"] == 0

    def test_fallback_no_cache(self):
        """encoding=None 时不使用缓存"""
        counter = TiktokenCounter(model="gpt-4", cache_size=8)
        counter._encoding = None

        result = counter.count("some text")
        assert result > 0
        assert counter.cache_info["size"] == 0


# ── slots 数据类测试 ──


class TestSlotsDataclasses:
    def test_context_block_no_dict(self):
        block = ContextBlock(
            content="test",
            role="system",
            token_count=5,
            priority=0.5,
            source="L1",
        )
        assert not hasattr(block, "__dict__")

    def test_context_block_with_content_with_slots(self):
        """验证 with_content() 在 slots 模式下正常工作"""
        block = ContextBlock(
            content="original",
            role="system",
            token_count=10,
            priority=0.8,
            source="L2",
        )
        new_block = block.with_content("compressed", 5)
        assert new_block.content == "compressed"
        assert new_block.token_count == 5
        assert new_block.priority == 0.8
        assert new_block.source == "L2"

    def test_context_block_with_priority_with_slots(self):
        """验证 with_priority() 在 slots 模式下正常工作"""
        block = ContextBlock(
            content="test",
            role="user",
            token_count=3,
            priority=0.5,
            source="L1",
        )
        new_block = block.with_priority(0.9)
        assert new_block.priority == 0.9
        assert new_block.content == "test"
