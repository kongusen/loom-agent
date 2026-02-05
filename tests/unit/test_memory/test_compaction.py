"""
MemoryCompactor 单元测试

测试记忆压缩功能
"""

from unittest.mock import MagicMock

import pytest

from loom.memory.compaction import CompactionConfig, MemoryCompactor
from loom.memory.segment_store import InMemorySegmentStore
from loom.protocol import Task


class TestCompactionConfig:
    """测试 CompactionConfig"""

    def test_default_config(self):
        """测试默认配置"""
        config = CompactionConfig()

        assert config.enabled is True
        assert config.threshold == 0.85
        assert config.cooldown_seconds == 300
        assert config.strategy == "silent"

    def test_custom_config(self):
        """测试自定义配置"""
        config = CompactionConfig(
            enabled=False, threshold=0.9, cooldown_seconds=600, strategy="explicit"
        )

        assert config.enabled is False
        assert config.threshold == 0.9
        assert config.cooldown_seconds == 600
        assert config.strategy == "explicit"


class TestMemoryCompactor:
    """测试 MemoryCompactor"""

    def setup_method(self):
        """设置测试环境"""
        self.config = CompactionConfig()
        self.memory_manager = MagicMock()
        self.token_counter = MagicMock()
        self.segment_store = InMemorySegmentStore(max_segments=100)

    @pytest.mark.asyncio
    async def test_compactor_initialization(self):
        """测试压缩器初始化"""
        compactor = MemoryCompactor(
            config=self.config,
            memory_manager=self.memory_manager,
            token_counter=self.token_counter,
            segment_store=self.segment_store,
        )

        assert compactor.config == self.config
        assert compactor.memory_manager == self.memory_manager
        assert compactor.token_counter == self.token_counter
        assert compactor.segment_store == self.segment_store
        assert compactor._last_compaction == {}

    @pytest.mark.asyncio
    async def test_compaction_disabled(self):
        """测试禁用压缩"""
        config = CompactionConfig(enabled=False)
        compactor = MemoryCompactor(
            config=config,
            memory_manager=self.memory_manager,
            token_counter=self.token_counter,
        )

        task = Task(taskId="task-1", sessionId="session-1", action="test")
        context = [{"role": "user", "content": "test"}]

        result = await compactor.check_and_compact(task, context, max_tokens=1000)

        assert result is False

    @pytest.mark.asyncio
    async def test_compaction_below_threshold(self):
        """测试低于阈值不触发压缩"""
        compactor = MemoryCompactor(
            config=self.config,
            memory_manager=self.memory_manager,
            token_counter=self.token_counter,
        )

        # 模拟 token 计数低于阈值
        self.token_counter.count_messages.return_value = 500  # 50% usage

        task = Task(taskId="task-1", sessionId="session-1", action="test")
        context = [{"role": "user", "content": "test"}]

        result = await compactor.check_and_compact(task, context, max_tokens=1000)

        assert result is False

    @pytest.mark.asyncio
    async def test_compaction_above_threshold(self):
        """测试超过阈值触发压缩"""
        compactor = MemoryCompactor(
            config=self.config,
            memory_manager=self.memory_manager,
            token_counter=self.token_counter,
            segment_store=self.segment_store,
        )

        # 模拟 token 计数超过阈值
        self.token_counter.count_messages.return_value = 900  # 90% usage

        task = Task(taskId="task-1", sessionId="session-1", action="test")
        context = [
            {"role": "user", "content": "test message 1"},
            {"role": "assistant", "content": "response 1"},
        ]

        result = await compactor.check_and_compact(task, context, max_tokens=1000)

        assert result is True
        assert "session-1" in compactor._last_compaction

    @pytest.mark.asyncio
    async def test_compaction_cooldown(self):
        """测试冷却期防止频繁压缩"""
        config = CompactionConfig(cooldown_seconds=60)
        compactor = MemoryCompactor(
            config=config,
            memory_manager=self.memory_manager,
            token_counter=self.token_counter,
        )

        # 模拟 token 计数超过阈值
        self.token_counter.count_messages.return_value = 900

        task = Task(taskId="task-1", sessionId="session-1", action="test")
        context = [{"role": "user", "content": "test"}]

        # 第一次压缩应该成功
        result1 = await compactor.check_and_compact(task, context, max_tokens=1000)
        assert result1 is True

        # 立即再次尝试应该被冷却期阻止
        result2 = await compactor.check_and_compact(task, context, max_tokens=1000)
        assert result2 is False

    @pytest.mark.asyncio
    async def test_perform_compaction_with_segment_store(self):
        """测试带 segment_store 的压缩"""
        compactor = MemoryCompactor(
            config=self.config,
            memory_manager=self.memory_manager,
            token_counter=self.token_counter,
            segment_store=self.segment_store,
        )

        task = Task(taskId="task-1", sessionId="session-1", action="test")
        context = [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"},
        ]

        # 执行压缩
        await compactor._perform_compaction(task, context)

        # 验证片段被存储
        assert len(self.segment_store._segments) == 2

    @pytest.mark.asyncio
    async def test_perform_compaction_without_segment_store(self):
        """测试不带 segment_store 的压缩"""
        compactor = MemoryCompactor(
            config=self.config,
            memory_manager=self.memory_manager,
            token_counter=self.token_counter,
            segment_store=None,  # 无 segment_store
        )

        task = Task(taskId="task-1", sessionId="session-1", action="test")
        context = [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"},
        ]

        # 执行压缩（不应该报错）
        await compactor._perform_compaction(task, context)

    @pytest.mark.asyncio
    async def test_extract_facts(self):
        """测试事实提取"""
        compactor = MemoryCompactor(
            config=self.config,
            memory_manager=self.memory_manager,
            token_counter=self.token_counter,
        )

        messages = [
            {"role": "user", "content": "Short message"},
            {"role": "assistant", "content": "A" * 300},  # 长消息
        ]
        segment_ids = ["seg-1", "seg-2"]

        facts = compactor._extract_facts(messages, segment_ids)

        assert len(facts) == 2
        assert facts[0]["role"] == "user"
        assert facts[0]["summary"] == "Short message"
        assert facts[0]["segment_id"] == "seg-1"
        assert facts[1]["role"] == "assistant"
        assert len(facts[1]["summary"]) == 200  # 应该被截断
        assert facts[1]["segment_id"] == "seg-2"
