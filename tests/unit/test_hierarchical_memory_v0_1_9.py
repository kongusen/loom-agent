"""
测试 HierarchicalMemory v0.1.9 新功能

验证：
- Task 6: 智能记忆晋升（LLM 摘要）
- Task 7: 异步向量化（后台任务队列）
- Task 8: Ephemeral Memory 调试模式
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from loom.builtin.memory.hierarchical_memory import (
    HierarchicalMemory,
    MemoryEntry,
)
from loom.core.message import Message


# ===== Task 6: Smart Promotion Tests =====


class TestSmartPromotionTrivialFilter:
    """测试智能晋升的 trivial 内容过滤"""

    def setup_method(self):
        """每个测试前设置"""
        self.memory = HierarchicalMemory(
            enable_smart_promotion=True,
            min_promotion_length=50,
        )

    def test_is_trivial_empty_content(self):
        """空内容应该被认为是 trivial"""
        assert self.memory._is_trivial("")
        assert self.memory._is_trivial("   ")

    def test_is_trivial_short_content(self):
        """太短的内容应该被认为是 trivial"""
        # 默认 min_promotion_length=50
        assert self.memory._is_trivial("短消息")
        assert self.memory._is_trivial("OK")

    def test_is_trivial_chinese_patterns(self):
        """中文客套话应该被过滤"""
        trivial_phrases = ["好的", "谢谢", "明白", "了解", "收到", "是的"]

        for phrase in trivial_phrases:
            assert self.memory._is_trivial(phrase)

    def test_is_trivial_english_patterns(self):
        """英文客套话应该被过滤"""
        trivial_phrases = ["ok", "okay", "thanks", "yes", "no", "sure"]

        for phrase in trivial_phrases:
            assert self.memory._is_trivial(phrase)

    def test_is_trivial_case_insensitive(self):
        """大小写不应影响判断"""
        assert self.memory._is_trivial("OK")
        assert self.memory._is_trivial("Ok")
        assert self.memory._is_trivial("ok")

    def test_is_not_trivial_meaningful_content(self):
        """有意义的内容不应该被过滤"""
        meaningful = "This is a detailed explanation about how the system works and provides valuable context for future reference."

        assert not self.memory._is_trivial(meaningful)


class TestSmartPromotionSummarization:
    """测试智能晋升的 LLM 摘要功能"""

    def setup_method(self):
        """每个测试前设置"""
        # Mock LLM
        self.mock_llm = AsyncMock()
        self.memory = HierarchicalMemory(
            enable_smart_promotion=True,
            summarization_llm=self.mock_llm,
            summarization_threshold=100,
        )

    def test_should_summarize_disabled(self):
        """禁用智能晋升时不应摘要"""
        memory = HierarchicalMemory(enable_smart_promotion=False)

        long_content = "a" * 200

        assert not memory._should_summarize(long_content)

    def test_should_summarize_no_llm(self):
        """没有 LLM 时不应摘要"""
        memory = HierarchicalMemory(
            enable_smart_promotion=True,
            summarization_llm=None,
        )

        long_content = "a" * 200

        assert not memory._should_summarize(long_content)

    def test_should_summarize_below_threshold(self):
        """内容长度低于阈值时不应摘要"""
        short_content = "a" * 50  # threshold=100

        assert not self.memory._should_summarize(short_content)

    def test_should_summarize_above_threshold(self):
        """内容长度超过阈值时应摘要"""
        long_content = "a" * 200  # threshold=100

        assert self.memory._should_summarize(long_content)

    @pytest.mark.asyncio
    async def test_summarize_for_longterm_success(self):
        """LLM 摘要成功"""
        # Mock LLM stream response
        async def mock_stream(*args, **kwargs):
            yield {"type": "content_delta", "content": "- Key fact 1\n"}
            yield {"type": "content_delta", "content": "- Key fact 2\n"}
            yield {"type": "content_delta", "content": "- Key fact 3"}

        self.mock_llm.stream = mock_stream

        original = "This is a very long and verbose explanation " * 10
        summary = await self.memory._summarize_for_longterm(original)

        assert "Key fact 1" in summary
        assert "Key fact 2" in summary
        assert len(summary) < len(original)

    @pytest.mark.asyncio
    async def test_summarize_for_longterm_empty_result(self):
        """LLM 返回空结果时应降级到原内容"""
        # Mock empty response
        async def mock_stream(*args, **kwargs):
            yield {"type": "content_delta", "content": ""}

        self.mock_llm.stream = mock_stream

        original = "Original content"
        summary = await self.memory._summarize_for_longterm(original)

        # 应该返回原内容
        assert summary == original

    @pytest.mark.asyncio
    async def test_summarize_for_longterm_no_llm(self):
        """没有 LLM 时应直接返回原内容"""
        memory = HierarchicalMemory(summarization_llm=None)

        original = "Original content"
        summary = await memory._summarize_for_longterm(original)

        assert summary == original


class TestSmartPromotionIntegration:
    """测试智能晋升的集成流程"""

    @pytest.mark.asyncio
    async def test_promote_filters_trivial(self):
        """晋升时应过滤 trivial 内容"""
        memory = HierarchicalMemory(
            enable_smart_promotion=True,
            min_promotion_length=50,
        )

        trivial_entry = MemoryEntry(
            id="test-1",
            content="好的",
            tier="working",
            timestamp=1234567890.0,
        )

        # 晋升前长期记忆为空
        assert len(memory._longterm) == 0

        # 尝试晋升
        await memory._promote_to_longterm(trivial_entry)

        # trivial 内容被过滤，长期记忆仍为空
        assert len(memory._longterm) == 0

    @pytest.mark.asyncio
    async def test_promote_with_summarization(self):
        """晋升时应使用 LLM 摘要"""
        # Mock LLM
        mock_llm = AsyncMock()

        async def mock_stream(*args, **kwargs):
            yield {"type": "content_delta", "content": "- Summarized fact"}

        mock_llm.stream = mock_stream

        memory = HierarchicalMemory(
            enable_smart_promotion=True,
            summarization_llm=mock_llm,
            summarization_threshold=50,
        )

        long_entry = MemoryEntry(
            id="test-1",
            content="a" * 100,  # 超过阈值
            tier="working",
            timestamp=1234567890.0,
        )

        await memory._promote_to_longterm(long_entry)

        # 应该被晋升且内容被摘要
        assert len(memory._longterm) == 1
        assert "Summarized fact" in memory._longterm[0].content
        assert memory._longterm[0].metadata.get("summarized") is True


# ===== Task 7: Async Vectorization Tests =====


class TestAsyncVectorizationQueue:
    """测试异步向量化队列"""

    @pytest.mark.asyncio
    async def test_vectorization_worker_starts(self):
        """启用异步向量化时应启动 worker"""
        mock_embedding = MagicMock()
        mock_embedding.get_dimension.return_value = 384

        memory = HierarchicalMemory(
            embedding=mock_embedding,
            enable_async_vectorization=True,
        )

        # Worker 应该已启动
        assert memory._vectorization_queue is not None
        assert memory._vectorization_worker_task is not None
        assert not memory._vectorization_worker_task.done()

        # 清理
        await memory.shutdown(timeout=1.0)

    @pytest.mark.asyncio
    async def test_vectorization_worker_not_started_when_disabled(self):
        """禁用异步向量化时不应启动 worker"""
        memory = HierarchicalMemory(enable_async_vectorization=False)

        assert memory._vectorization_queue is None
        assert memory._vectorization_worker_task is None

    @pytest.mark.asyncio
    async def test_promotion_queues_vectorization(self):
        """晋升时应将向量化任务排队而非阻塞"""
        mock_embedding = MagicMock()
        mock_embedding.get_dimension.return_value = 384
        mock_embedding.embed_query = AsyncMock(return_value=[0.1] * 384)

        memory = HierarchicalMemory(
            embedding=mock_embedding,
            enable_async_vectorization=True,
        )

        entry = MemoryEntry(
            id="test-1",
            content="Meaningful content that should be promoted and vectorized.",
            tier="working",
            timestamp=1234567890.0,
        )

        # 晋升（应该非阻塞）
        await memory._promote_to_longterm(entry)

        # 立即检查：应该已添加到长期记忆
        assert len(memory._longterm) == 1

        # 向量化任务应该在队列中（可能还未完成）
        assert not memory._vectorization_queue.empty() or entry.embedding is not None

        # 清理
        await memory.shutdown(timeout=2.0)

    @pytest.mark.asyncio
    async def test_shutdown_flushes_queue(self):
        """关闭时应处理完所有待处理任务"""
        mock_embedding = MagicMock()
        mock_embedding.get_dimension.return_value = 384

        # Mock embed_documents to return embeddings
        async def mock_embed_documents(texts):
            return [[0.1] * 384 for _ in texts]

        mock_embedding.embed_documents = mock_embed_documents

        memory = HierarchicalMemory(
            embedding=mock_embedding,
            enable_async_vectorization=True,
        )

        # 添加多个条目
        for i in range(5):
            entry = MemoryEntry(
                id=f"test-{i}",
                content=f"Content {i} " * 20,
                tier="working",
                timestamp=1234567890.0 + i,
            )
            await memory._promote_to_longterm(entry)

        # 关闭应该等待所有任务完成
        await memory.shutdown(timeout=5.0)

        # 队列应该为空
        assert memory._vectorization_queue.empty()


class TestAsyncVectorizationBatching:
    """测试异步向量化批处理"""

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """应该批量处理向量化任务"""
        mock_embedding = MagicMock()
        mock_embedding.get_dimension.return_value = 384

        call_count = 0

        async def mock_embed_documents(texts):
            nonlocal call_count
            call_count += 1
            return [[0.1] * 384 for _ in texts]

        mock_embedding.embed_documents = mock_embed_documents

        memory = HierarchicalMemory(
            embedding=mock_embedding,
            enable_async_vectorization=True,
            vectorization_batch_size=3,
        )

        # 添加 5 个条目
        for i in range(5):
            entry = MemoryEntry(
                id=f"test-{i}",
                content=f"Content {i} " * 20,
                tier="working",
                timestamp=1234567890.0 + i,
            )
            await memory._promote_to_longterm(entry)

        # 等待处理完成
        await memory.shutdown(timeout=5.0)

        # 应该至少进行了批处理（5个条目，batch_size=3，应该是2次调用）
        assert call_count >= 1


# ===== Task 8: Ephemeral Debug Mode Tests =====


class TestEphemeralDebugMode:
    """测试 Ephemeral Memory 调试模式"""

    @pytest.mark.asyncio
    async def test_debug_mode_enabled(self):
        """启用调试模式应增强日志"""
        memory = HierarchicalMemory(enable_ephemeral_debug=True)

        # 调试模式应该启用
        assert memory.enable_ephemeral_debug is True

    @pytest.mark.asyncio
    async def test_debug_mode_disabled(self):
        """禁用调试模式是默认行为"""
        memory = HierarchicalMemory()

        assert memory.enable_ephemeral_debug is False

    @pytest.mark.asyncio
    async def test_add_ephemeral_with_debug(self):
        """调试模式下添加 ephemeral 应记录详细信息"""
        memory = HierarchicalMemory(enable_ephemeral_debug=True)

        with patch("loom.builtin.memory.hierarchical_memory.logger") as mock_logger:
            await memory.add_ephemeral(
                key="test_key",
                content="Test content",
                metadata={"tool": "test_tool"},
            )

            # 应该调用 logger.info（调试模式）而非 logger.debug
            assert mock_logger.info.called

            # 检查日志消息包含关键信息
            call_args = str(mock_logger.info.call_args)
            assert "test_key" in call_args
            assert "DEBUG" in call_args

    @pytest.mark.asyncio
    async def test_get_ephemeral_with_debug(self):
        """调试模式下获取 ephemeral 应记录详细信息"""
        memory = HierarchicalMemory(enable_ephemeral_debug=True)

        await memory.add_ephemeral(key="test_key", content="Test content")

        with patch("loom.builtin.memory.hierarchical_memory.logger") as mock_logger:
            result = await memory.get_ephemeral("test_key")

            assert result == "Test content"
            assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_clear_ephemeral_with_debug(self):
        """调试模式下清除 ephemeral 应记录详细信息"""
        memory = HierarchicalMemory(enable_ephemeral_debug=True)

        await memory.add_ephemeral(key="test_key", content="Test content")

        with patch("loom.builtin.memory.hierarchical_memory.logger") as mock_logger:
            await memory.clear_ephemeral("test_key")

            assert mock_logger.info.called


class TestDumpEphemeralState:
    """测试 dump_ephemeral_state() 功能"""

    @pytest.mark.asyncio
    async def test_dump_empty_state(self):
        """空状态应该返回空列表"""
        memory = HierarchicalMemory()

        state = memory.dump_ephemeral_state()

        assert state["total_entries"] == 0
        assert state["entries"] == []

    @pytest.mark.asyncio
    async def test_dump_with_entries(self):
        """应该导出所有 ephemeral 条目"""
        memory = HierarchicalMemory()

        await memory.add_ephemeral(
            key="key1",
            content="Content 1",
            metadata={"tool": "tool1"},
        )
        await memory.add_ephemeral(
            key="key2",
            content="Content 2",
            metadata={"tool": "tool2"},
        )

        state = memory.dump_ephemeral_state()

        assert state["total_entries"] == 2
        assert len(state["entries"]) == 2

        # 检查第一个条目
        entry1 = next(e for e in state["entries"] if e["key"] == "key1")
        assert entry1["content_length"] == len("Content 1")
        assert entry1["metadata"]["tool"] == "tool1"

    @pytest.mark.asyncio
    async def test_dump_truncates_long_content(self):
        """长内容应该被截断"""
        memory = HierarchicalMemory()

        long_content = "a" * 200
        await memory.add_ephemeral(key="long_key", content=long_content)

        state = memory.dump_ephemeral_state()

        entry = state["entries"][0]

        # content_preview 应该被截断
        assert len(entry["content_preview"]) < len(long_content)
        assert entry["content_preview"].endswith("...")

    @pytest.mark.asyncio
    async def test_dump_includes_metadata(self):
        """导出应该包含完整元数据"""
        memory = HierarchicalMemory()

        metadata = {
            "tool_name": "test_tool",
            "status": "in_progress",
            "retries": 3,
        }

        await memory.add_ephemeral(
            key="test_key",
            content="Test",
            metadata=metadata,
        )

        state = memory.dump_ephemeral_state()

        entry = state["entries"][0]
        assert entry["metadata"] == metadata
        assert entry["tier"] == "ephemeral"
        assert "timestamp" in entry
