"""
SegmentStore 单元测试

测试记忆片段存储功能
"""

import time

import pytest

from loom.memory.segment_store import InMemorySegmentStore, MemorySegment


class TestMemorySegment:
    """测试 MemorySegment 数据类"""

    def test_create_segment_with_defaults(self):
        """测试使用默认值创建片段"""
        segment = MemorySegment()

        assert segment.segmentId  # 应该有自动生成的 ID
        assert segment.content == ""
        assert segment.timestamp == 0.0
        assert segment.taskId == ""
        assert segment.metadata == {}

    def test_create_segment_with_values(self):
        """测试使用指定值创建片段"""
        segment = MemorySegment(
            segmentId="seg-123",
            content="Test content",
            timestamp=123.456,
            taskId="task-1",
            metadata={"key": "value"},
        )

        assert segment.segmentId == "seg-123"
        assert segment.content == "Test content"
        assert segment.timestamp == 123.456
        assert segment.taskId == "task-1"
        assert segment.metadata == {"key": "value"}


class TestInMemorySegmentStore:
    """测试 InMemorySegmentStore"""

    @pytest.mark.asyncio
    async def test_store_segment(self):
        """测试存储片段"""
        store = InMemorySegmentStore(max_segments=10)

        segment = MemorySegment(content="Test content", timestamp=time.time(), taskId="task-1")

        segment_id = await store.store(segment)

        assert segment_id == segment.segmentId
        assert segment_id in store._segments

    @pytest.mark.asyncio
    async def test_retrieve_segments(self):
        """测试检索片段"""
        store = InMemorySegmentStore(max_segments=10)

        # 存储多个片段
        segment1 = MemorySegment(content="Content 1", timestamp=time.time(), taskId="task-1")
        segment2 = MemorySegment(content="Content 2", timestamp=time.time(), taskId="task-2")

        id1 = await store.store(segment1)
        id2 = await store.store(segment2)

        # 检索片段
        retrieved = await store.retrieve([id1, id2])

        assert len(retrieved) == 2
        assert retrieved[0].content == "Content 1"
        assert retrieved[1].content == "Content 2"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_segment(self):
        """测试检索不存在的片段"""
        store = InMemorySegmentStore(max_segments=10)

        retrieved = await store.retrieve(["nonexistent-id"])

        assert len(retrieved) == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_segments(self):
        """测试清理旧片段"""
        store = InMemorySegmentStore(max_segments=10)

        # 存储不同时间戳的片段
        old_segment = MemorySegment(content="Old", timestamp=100.0, taskId="task-1")
        new_segment = MemorySegment(content="New", timestamp=200.0, taskId="task-2")

        await store.store(old_segment)
        await store.store(new_segment)

        # 清理 150.0 之前的片段
        cleaned = await store.cleanup(before_timestamp=150.0)

        assert cleaned == 1
        assert old_segment.segmentId not in store._segments
        assert new_segment.segmentId in store._segments

    @pytest.mark.asyncio
    async def test_max_segments_fifo(self):
        """测试超过最大容量时的 FIFO 清理"""
        store = InMemorySegmentStore(max_segments=3)

        # 存储 4 个片段
        segments = []
        for i in range(4):
            segment = MemorySegment(content=f"Content {i}", timestamp=float(i), taskId=f"task-{i}")
            segments.append(segment)
            await store.store(segment)

        # 应该只保留最后 3 个
        assert len(store._segments) == 3
        assert segments[0].segmentId not in store._segments  # 最旧的被删除
        assert segments[1].segmentId in store._segments
        assert segments[2].segmentId in store._segments
        assert segments[3].segmentId in store._segments
