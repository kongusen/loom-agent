"""
Context Management Unit Tests

测试上下文管理功能
"""

from datetime import UTC, datetime

import pytest

from loom.memory.context import (
    ContextManager,
    PriorityContextStrategy,
    SlidingWindowStrategy,
)
from loom.memory.tokenizer import TokenCounter
from loom.memory.types import MemoryUnit


class MockTokenCounter(TokenCounter):
    """Mock TokenCounter for testing"""

    def count(self, text: str) -> int:
        """Simple word-based token counting"""
        return len(text.split())

    def count_messages(self, messages: list[dict]) -> int:
        """Count tokens in messages"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.count(content)
        return total


class TestPriorityContextStrategy:
    """测试 PriorityContextStrategy"""

    def test_select_context_empty_list(self):
        """测试空列表"""
        strategy = PriorityContextStrategy()
        counter = MockTokenCounter()

        result = strategy.select_context([], max_tokens=100, token_counter=counter)

        assert result == []

    def test_select_context_by_importance(self):
        """测试按重要性选择"""
        strategy = PriorityContextStrategy()
        counter = MockTokenCounter()

        # 创建不同重要性的记忆单元
        units = [
            MemoryUnit(content="low importance", importance=0.3, created_at=datetime.now(UTC)),
            MemoryUnit(content="high importance", importance=0.9, created_at=datetime.now(UTC)),
            MemoryUnit(content="medium importance", importance=0.6, created_at=datetime.now(UTC)),
        ]

        result = strategy.select_context(units, max_tokens=100, token_counter=counter)

        # 应该按重要性排序：high > medium > low
        assert len(result) == 3
        assert result[0].importance == 0.9
        assert result[1].importance == 0.6
        assert result[2].importance == 0.3

    def test_select_context_respects_token_limit(self):
        """测试遵守token限制"""
        strategy = PriorityContextStrategy()
        counter = MockTokenCounter()

        # 创建多个记忆单元，总token数超过限制
        units = [
            MemoryUnit(
                content="word " * 10, importance=0.9, created_at=datetime.now(UTC)
            ),  # 10 tokens
            MemoryUnit(
                content="word " * 10, importance=0.8, created_at=datetime.now(UTC)
            ),  # 10 tokens
            MemoryUnit(
                content="word " * 10, importance=0.7, created_at=datetime.now(UTC)
            ),  # 10 tokens
        ]

        # 限制为15 tokens，应该只选择前两个（但第二个会超限，所以只选第一个）
        result = strategy.select_context(units, max_tokens=15, token_counter=counter)

        assert len(result) == 1
        assert result[0].importance == 0.9


class TestSlidingWindowStrategy:
    """测试 SlidingWindowStrategy"""

    def test_select_context_empty_list(self):
        """测试空列表"""
        strategy = SlidingWindowStrategy()
        counter = MockTokenCounter()

        result = strategy.select_context([], max_tokens=100, token_counter=counter)

        assert result == []

    def test_select_context_by_recency(self):
        """测试按时间选择最近的"""
        strategy = SlidingWindowStrategy()
        counter = MockTokenCounter()

        # 创建不同时间的记忆单元
        now = datetime.now(UTC)
        units = [
            MemoryUnit(
                content="old", importance=0.5, created_at=datetime(2024, 1, 1, tzinfo=UTC)
            ),
            MemoryUnit(content="recent", importance=0.5, created_at=now),
            MemoryUnit(
                content="middle", importance=0.5, created_at=datetime(2024, 6, 1, tzinfo=UTC)
            ),
        ]

        result = strategy.select_context(units, max_tokens=100, token_counter=counter)

        # 应该按时间顺序返回（旧的在前）
        assert len(result) == 3
        assert result[0].content == "old"
        assert result[1].content == "middle"
        assert result[2].content == "recent"

    def test_select_context_respects_token_limit(self):
        """测试遵守token限制"""
        strategy = SlidingWindowStrategy()
        counter = MockTokenCounter()

        now = datetime.now(UTC)
        units = [
            MemoryUnit(
                content="word " * 10,
                importance=0.5,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            MemoryUnit(
                content="word " * 10,
                importance=0.5,
                created_at=datetime(2024, 6, 1, tzinfo=UTC),
            ),
            MemoryUnit(content="word " * 10, importance=0.5, created_at=now),
        ]

        # 限制为15 tokens，应该只选择最近的一个
        result = strategy.select_context(units, max_tokens=15, token_counter=counter)

        assert len(result) == 1
        assert result[0].created_at == now

    def test_maintains_chronological_order(self):
        """测试保持时间顺序"""
        strategy = SlidingWindowStrategy()
        counter = MockTokenCounter()

        units = [
            MemoryUnit(
                content="first", importance=0.5, created_at=datetime(2024, 1, 1, tzinfo=UTC)
            ),
            MemoryUnit(
                content="second", importance=0.5, created_at=datetime(2024, 2, 1, tzinfo=UTC)
            ),
            MemoryUnit(
                content="third", importance=0.5, created_at=datetime(2024, 3, 1, tzinfo=UTC)
            ),
        ]

        result = strategy.select_context(units, max_tokens=100, token_counter=counter)

        # 结果应该按时间顺序（旧的在前）
        assert result[0].content == "first"
        assert result[1].content == "second"
        assert result[2].content == "third"


class TestContextManager:
    """测试 ContextManager"""

    def test_init_with_default_strategy(self):
        """测试默认策略初始化"""
        counter = MockTokenCounter()
        manager = ContextManager(token_counter=counter)

        assert manager.token_counter == counter
        assert isinstance(manager.strategy, SlidingWindowStrategy)
        assert manager.max_tokens == 4000

    def test_init_with_custom_strategy(self):
        """测试自定义策略初始化"""
        counter = MockTokenCounter()
        strategy = PriorityContextStrategy()
        manager = ContextManager(token_counter=counter, strategy=strategy, max_tokens=2000)

        assert manager.strategy == strategy
        assert manager.max_tokens == 2000

    def test_build_context_uses_strategy(self):
        """测试构建上下文使用策略"""
        counter = MockTokenCounter()
        strategy = PriorityContextStrategy()
        manager = ContextManager(token_counter=counter, strategy=strategy)

        units = [
            MemoryUnit(content="low", importance=0.3, created_at=datetime.now(UTC)),
            MemoryUnit(content="high", importance=0.9, created_at=datetime.now(UTC)),
        ]

        result = manager.build_context(units)

        # 应该使用优先级策略，高重要性在前
        assert len(result) == 2
        assert result[0].importance == 0.9

    def test_build_context_with_custom_max_tokens(self):
        """测试使用自定义max_tokens"""
        counter = MockTokenCounter()
        manager = ContextManager(token_counter=counter, max_tokens=1000)

        units = [
            MemoryUnit(content="word " * 100, importance=0.5, created_at=datetime.now(UTC)),
            MemoryUnit(content="word " * 100, importance=0.5, created_at=datetime.now(UTC)),
        ]

        # 使用更小的限制
        result = manager.build_context(units, max_tokens=50)

        # 应该只选择一个单元（因为每个100 tokens）
        assert len(result) <= 1

    def test_build_context_empty_units(self):
        """测试空单元列表"""
        counter = MockTokenCounter()
        manager = ContextManager(token_counter=counter)

        result = manager.build_context([])

        assert result == []
