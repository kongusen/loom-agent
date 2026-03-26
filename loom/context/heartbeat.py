"""HeartbeatLoop — Ralph Loop 心跳续写（公理一）"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..types import MemoryEntry

if TYPE_CHECKING:
    from ..memory import MemoryManager
    from ..skills.context_manager import SkillContextManager
    from .compression import CompressionScorer
    from .partition import PartitionManager


class HeartbeatLoop:
    """Ralph Loop：上下文磁盘换页"""

    def __init__(
        self,
        partition_mgr: PartitionManager,
        memory_mgr: MemoryManager,
        skill_mgr: SkillContextManager,
        compressor: CompressionScorer,
    ):
        self.partition_mgr = partition_mgr
        self.memory_mgr = memory_mgr
        self.skill_mgr = skill_mgr
        self.compressor = compressor

    async def trigger(self, goal: str) -> dict[str, str]:
        """触发心跳续写，返回新的上下文"""
        # 1. snapshot C_working → M_f
        working = self.partition_mgr.partitions["working"]
        await self.memory_mgr.l3.store(
            MemoryEntry(
                content=working.content,
                tokens=working.tokens,
                importance=1.0,
                metadata={"type": "working_state", "goal": goal, "timestamp": time.time()},
            )
        )

        # 2. 压缩 C_history（三层评分）
        history_msgs = self.memory_mgr.l1.get_messages()
        scored = await self.compressor.score_history(history_msgs, goal)

        # 保留 score 最高的 40%
        scored.sort(key=lambda x: x[1], reverse=True)
        keep_count = max(1, int(len(scored) * 0.4))
        compressed_msgs = [msg for msg, _ in scored[:keep_count]]

        # 3. 重建上下文
        new_context = {
            "system": self.partition_mgr.partitions["system"].content,
            "memory": await self._rebuild_memory(goal),
            "skill": self.skill_mgr.get_context(),
            "history": self._format_messages(compressed_msgs),
            "working": working.content,
        }

        return new_context

    async def _rebuild_memory(self, goal: str) -> str:
        """从 L2/L3 重新检索记忆"""
        budget = self.partition_mgr.get_available_budget("memory")
        entries = await self.memory_mgr.extract_for(goal, budget)
        return "\n".join(e.content for e in entries)

    def _format_messages(self, msgs: list) -> str:
        """格式化消息为字符串"""
        parts = []
        for m in msgs:
            content = m.content if isinstance(m.content, str) else str(m.content)
            parts.append(f"{m.role}: {content}")
        return "\n".join(parts)
