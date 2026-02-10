"""
Memory Compaction - 记忆压缩

静默记忆整理机制：
- 自动检测上下文使用率
- 超过阈值时触发压缩
- 支持冷却期防止频繁压缩
- 可选的 Fact Indexing（事实索引）

符合 Loom 框架原则：提供机制，应用选择策略
"""

import logging
import time
from dataclasses import dataclass
from typing import Literal

from loom.fractal.memory import MemoryScope
from loom.memory.manager import MemoryManager
from loom.memory.segment_store import MemorySegment, SegmentStore
from loom.memory.tokenizer import TokenCounter
from loom.runtime import Task

logger = logging.getLogger(__name__)


@dataclass
class CompactionConfig:
    """
    记忆压缩配置

    属性：
        enabled: 是否启用压缩
        threshold: 触发阈值（上下文使用率）
        cooldown_seconds: 冷却时间（秒）
        strategy: 压缩策略
            - "silent": 静默压缩（自动触发）
            - "explicit": 显式压缩（需要手动触发）
            - "none": 不压缩
    """

    enabled: bool = True
    threshold: float = 0.85
    cooldown_seconds: int = 300
    strategy: Literal["silent", "explicit", "none"] = "silent"


class MemoryCompactor:
    """
    记忆压缩器

    负责检测上下文使用率并触发压缩。
    支持冷却期防止频繁压缩。
    """

    def __init__(
        self,
        config: CompactionConfig,
        memory_manager: MemoryManager,
        token_counter: TokenCounter,
        segment_store: SegmentStore | None = None,
    ):
        """
        初始化压缩器

        Args:
            config: 压缩配置
            memory_manager: 记忆管理器
            token_counter: Token 计数器
            segment_store: 可选的片段存储（用于 Fact Indexing）
        """
        self.config = config
        self.memory_manager = memory_manager
        self.token_counter = token_counter
        self.segment_store = segment_store
        self._last_compaction: dict[str, float] = {}

    async def check_and_compact(
        self,
        task: Task,
        current_context: list[dict],
        max_tokens: int,
    ) -> bool:
        """
        检查并执行压缩

        Args:
            task: 当前任务
            current_context: 当前上下文
            max_tokens: 最大 token 数

        Returns:
            bool: 是否执行了压缩
        """
        if not self.config.enabled:
            return False

        # 计算使用率
        current_tokens = self.token_counter.count_messages(current_context)
        usage_ratio = current_tokens / max_tokens

        if usage_ratio < self.config.threshold:
            return False

        # 检查冷却
        session_id = task.sessionId or "default"
        if self._is_in_cooldown(session_id):
            return False

        # 执行压缩
        await self._perform_compaction(task, current_context)
        self._last_compaction[session_id] = time.time()
        return True

    def _is_in_cooldown(self, session_id: str) -> bool:
        """
        检查是否在冷却期

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否在冷却期
        """
        if session_id not in self._last_compaction:
            return False
        elapsed = time.time() - self._last_compaction[session_id]
        return elapsed < self.config.cooldown_seconds

    async def _perform_compaction(
        self,
        task: Task,
        current_context: list[dict],
    ) -> None:
        """
        执行压缩

        实现逻辑：
        1. 提取上下文中的关键信息
        2. 如果有 segment_store，存储原始片段
        3. 创建压缩后的事实（包含 segment_ids 引用）
        4. 存储到记忆管理器

        Args:
            task: 当前任务
            current_context: 当前上下文
        """
        if self.config.strategy == "none":
            return

        logger.info(f"Starting memory compaction for task {task.taskId}")

        # 1. 提取需要压缩的消息（排除系统消息）
        messages_to_compress = [msg for msg in current_context if msg.get("role") != "system"]

        if not messages_to_compress:
            logger.debug("No messages to compress")
            return

        # 2. 如果有 segment_store，存储原始片段
        segment_ids = []
        if self.segment_store:
            for i, msg in enumerate(messages_to_compress):
                segment = MemorySegment(
                    content=str(msg.get("content", "")),
                    timestamp=time.time(),
                    taskId=task.taskId,
                    metadata={
                        "role": msg.get("role", "unknown"),
                        "index": i,
                        "session_id": task.sessionId,
                    },
                )
                segment_id = await self.segment_store.store(segment)
                segment_ids.append(segment_id)
                logger.debug(f"Stored segment {segment_id}")

        # 3. 创建压缩后的事实
        # 简单实现：提取关键信息作为事实
        facts = self._extract_facts(messages_to_compress, segment_ids)

        # 4. 存储事实到记忆管理器
        for i, fact in enumerate(facts):
            entry_id = f"compacted:{task.taskId}:{i}"
            try:
                await self.memory_manager.write(
                    entry_id=entry_id,
                    content=fact,
                    scope=MemoryScope.LOCAL,
                )
            except Exception as e:
                logger.warning(f"Failed to write compacted fact {entry_id}: {e}")

        logger.info(
            f"Compressed {len(messages_to_compress)} messages into "
            f"{len(facts)} facts with {len(segment_ids)} segments"
        )

    def _extract_facts(
        self,
        messages: list[dict],
        segment_ids: list[str],
    ) -> list[dict]:
        """
        提取事实（简单实现）

        Args:
            messages: 消息列表
            segment_ids: 对应的片段ID列表

        Returns:
            list[dict]: 事实列表
        """
        facts = []

        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # 简单的事实提取：保留角色和内容摘要
            fact = {
                "role": role,
                "summary": content[:200] if len(content) > 200 else content,
                "full_content_available": len(segment_ids) > i,
            }

            # 如果有 segment_id，添加引用
            if len(segment_ids) > i:
                fact["segment_id"] = segment_ids[i]

            facts.append(fact)

        return facts
