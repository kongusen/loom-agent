"""
Memory Segment Store - 记忆片段存储

提供 Protocol 接口，允许应用层选择存储实现：
- InMemorySegmentStore: 内存实现（测试/快速开始）
- RedisSegmentStore: Redis 实现（生产环境）
- PostgreSQLSegmentStore: 数据库实现（持久化）

符合 Loom 框架原则：提供机制，应用选择策略
"""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4


@dataclass
class MemorySegment:
    """
    原始记忆片段

    属性：
        segmentId: 片段唯一标识
        content: 原始内容
        timestamp: 创建时间戳
        taskId: 关联的任务ID
        metadata: 元数据（可选）
    """

    segmentId: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    timestamp: float = 0.0
    taskId: str = ""
    metadata: dict = field(default_factory=dict)


class SegmentStore(Protocol):
    """
    片段存储接口（由应用层实现）

    这是一个 Protocol 接口，不提供具体实现。
    应用层可以选择：
    - InMemorySegmentStore（内存，用于测试）
    - RedisSegmentStore（Redis，用于生产）
    - PostgreSQLSegmentStore（数据库，用于持久化）
    """

    async def store(self, segment: MemorySegment) -> str:
        """
        存储片段

        Args:
            segment: 要存储的片段

        Returns:
            str: 片段ID
        """
        ...

    async def retrieve(self, segment_ids: list[str]) -> list[MemorySegment]:
        """
        检索片段

        Args:
            segment_ids: 片段ID列表

        Returns:
            List[MemorySegment]: 检索到的片段列表
        """
        ...

    async def cleanup(self, before_timestamp: float) -> int:
        """
        清理旧片段

        Args:
            before_timestamp: 清理此时间戳之前的片段

        Returns:
            int: 清理的片段数量
        """
        ...


class InMemorySegmentStore:
    """
    内存片段存储（参考实现）

    用于测试和快速开始。生产环境建议使用持久化存储。

    特性：
    - FIFO 清理策略（超过容量时删除最旧的）
    - 简单的字典存储
    - 无持久化
    """

    def __init__(self, max_segments: int = 1000):
        """
        初始化内存存储

        Args:
            max_segments: 最大片段数量
        """
        self._segments: dict[str, MemorySegment] = {}
        self.max_segments = max_segments

    async def store(self, segment: MemorySegment) -> str:
        """存储片段"""
        self._segments[segment.segmentId] = segment

        # 简单的 FIFO 清理
        if len(self._segments) > self.max_segments:
            # 按时间戳排序，删除最旧的
            sorted_segments = sorted(self._segments.items(), key=lambda x: x[1].timestamp)
            oldest_id = sorted_segments[0][0]
            del self._segments[oldest_id]

        return segment.segmentId

    async def retrieve(self, segment_ids: list[str]) -> list[MemorySegment]:
        """检索片段"""
        result = []
        for seg_id in segment_ids:
            if seg_id in self._segments:
                result.append(self._segments[seg_id])
        return result

    async def cleanup(self, before_timestamp: float) -> int:
        """清理旧片段"""
        to_delete = [
            seg_id
            for seg_id, segment in self._segments.items()
            if segment.timestamp < before_timestamp
        ]

        for seg_id in to_delete:
            del self._segments[seg_id]

        return len(to_delete)
