"""
SharedPoolSource - 共享记忆池上下文源

从 SharedMemoryPool 收集条目，转换为 ContextBlock 注入 LLM 上下文。
按 updated_at 降序排列，最新条目优先级最高。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.shared_pool import SharedMemoryPool
    from loom.memory.tokenizer import TokenCounter


class SharedPoolSource(ContextSource):
    """共享记忆池上下文源"""

    def __init__(
        self,
        pool: SharedMemoryPool,
        prefix: str | None = None,
    ):
        self._pool = pool
        self._prefix = prefix

    @property
    def source_name(self) -> str:
        return "shared_pool"

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: TokenCounter,
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        entries = await self._pool.list_entries(prefix=self._prefix, limit=50)
        if not entries:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0
        total = len(entries)

        for idx, entry in enumerate(entries):
            content = str(entry.content) if entry.content else ""
            if not content:
                continue

            label = f"[SHARED:{entry.key}] {content}"
            tokens = self._count_tokens(label, "system", token_counter)

            if current_tokens + tokens > token_budget:
                break

            # 最新条目优先级最高：0.95 → 0.55
            priority = 0.95 - (idx / max(total, 1)) * 0.4

            block = ContextBlock(
                content=label,
                role="system",
                token_count=tokens,
                priority=priority,
                source=self.source_name,
                compressible=True,
                metadata={
                    "pool_id": self._pool.pool_id,
                    "key": entry.key,
                    "version": entry.version,
                    "writer": entry.updated_by,
                },
            )
            blocks.append(block)
            current_tokens += tokens

        return blocks
