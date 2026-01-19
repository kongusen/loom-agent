"""
上下文管理测试

测试上下文选择策略和上下文管理器。
"""

from datetime import datetime, timedelta

from loom.memory.context import (
    ContextManager,
    PriorityContextStrategy,
    SlidingWindowStrategy,
)
from loom.memory.tokenizer import EstimateCounter
from loom.memory.types import MemoryUnit


class TestPriorityContextStrategy:
    """测试基于优先级的上下文策略"""

    def test_select_by_importance(self):
        """测试按重要性选择记忆单元"""
        strategy = PriorityContextStrategy()
        counter = EstimateCounter()

        units = [
            MemoryUnit(
                id="unit-1",
                content="Low importance message",
                importance=0.3,
            ),
            MemoryUnit(
                id="unit-2",
                content="High importance message",
                importance=0.9,
            ),
            MemoryUnit(
                id="unit-3",
                content="Medium importance message",
                importance=0.6,
            ),
        ]

        # 选择上下文（限制100 tokens）
        selected = strategy.select_context(units, max_tokens=100, token_counter=counter)

        # 验证：应该按importance降序选择
        assert len(selected) > 0
        assert selected[0].id == "unit-2"  # 最高优先级

    def test_respects_token_limit(self):
        """测试遵守token限制"""
        strategy = PriorityContextStrategy()
        counter = EstimateCounter()

        units = [
            MemoryUnit(
                id="unit-1",
                content="A" * 100,  # ~25 tokens
                importance=0.9,
            ),
            MemoryUnit(
                id="unit-2",
                content="B" * 100,  # ~25 tokens
                importance=0.8,
            ),
            MemoryUnit(
                id="unit-3",
                content="C" * 100,  # ~25 tokens
                importance=0.7,
            ),
        ]

        # 限制为40 tokens，应该只能选择前两个
        selected = strategy.select_context(units, max_tokens=40, token_counter=counter)

        assert len(selected) <= 2


class TestSlidingWindowStrategy:
    """测试滑动窗口策略"""

    def test_select_recent_units(self):
        """测试选择最近的记忆单元"""
        strategy = SlidingWindowStrategy()
        counter = EstimateCounter()

        now = datetime.now()
        units = [
            MemoryUnit(
                id="unit-1",
                content="Old message",
                created_at=now - timedelta(hours=3),
            ),
            MemoryUnit(
                id="unit-2",
                content="Recent message",
                created_at=now - timedelta(hours=1),
            ),
            MemoryUnit(
                id="unit-3",
                content="Latest message",
                created_at=now,
            ),
        ]

        # 选择上下文
        selected = strategy.select_context(units, max_tokens=100, token_counter=counter)

        # 验证：应该包含最新的消息
        assert len(selected) > 0
        assert selected[-1].id == "unit-3"  # 最新的在最后

    def test_maintains_time_order(self):
        """测试保持时间顺序"""
        strategy = SlidingWindowStrategy()
        counter = EstimateCounter()

        now = datetime.now()
        units = [
            MemoryUnit(id="unit-1", content="First", created_at=now - timedelta(hours=2)),
            MemoryUnit(id="unit-2", content="Second", created_at=now - timedelta(hours=1)),
            MemoryUnit(id="unit-3", content="Third", created_at=now),
        ]

        selected = strategy.select_context(units, max_tokens=100, token_counter=counter)

        # 验证：时间顺序应该是从旧到新
        assert selected[0].created_at < selected[-1].created_at


class TestContextManager:
    """测试上下文管理器"""

    def test_build_context_with_priority_strategy(self):
        """测试使用优先级策略构建上下文"""
        counter = EstimateCounter()
        strategy = PriorityContextStrategy()
        manager = ContextManager(
            token_counter=counter,
            strategy=strategy,
            max_tokens=100,
        )

        units = [
            MemoryUnit(id="unit-1", content="Low priority", importance=0.3),
            MemoryUnit(id="unit-2", content="High priority", importance=0.9),
        ]

        context = manager.build_context(units)

        # 验证：应该优先选择高优先级
        assert len(context) > 0
        assert context[0].id == "unit-2"

    def test_build_context_with_sliding_window(self):
        """测试使用滑动窗口策略构建上下文"""
        counter = EstimateCounter()
        strategy = SlidingWindowStrategy()
        manager = ContextManager(
            token_counter=counter,
            strategy=strategy,
            max_tokens=100,
        )

        now = datetime.now()
        units = [
            MemoryUnit(id="unit-1", content="Old", created_at=now - timedelta(hours=2)),
            MemoryUnit(id="unit-2", content="New", created_at=now),
        ]

        context = manager.build_context(units)

        # 验证：应该包含最新的消息
        assert len(context) > 0
        assert context[-1].id == "unit-2"

    def test_override_max_tokens(self):
        """测试覆盖默认的max_tokens"""
        counter = EstimateCounter()
        manager = ContextManager(
            token_counter=counter,
            max_tokens=1000,  # 默认值
        )

        units = [
            MemoryUnit(id="unit-1", content="A" * 100),  # ~25 tokens
            MemoryUnit(id="unit-2", content="B" * 100),  # ~25 tokens
        ]

        # 使用更小的限制
        context = manager.build_context(units, max_tokens=30)

        # 验证：应该只选择一个单元
        assert len(context) == 1
