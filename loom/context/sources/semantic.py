"""
Semantic Context Source - L4 语义检索源

从向量存储中检索语义相关的上下文。
"""

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory
    from loom.memory.tokenizer import TokenCounter


class L4SemanticSource(ContextSource):
    """
    L4 语义检索源

    从 LoomMemory 的 L4 向量存储中检索语义相关的内容。
    优先级基于向量相似度。
    """

    def __init__(
        self,
        memory: "LoomMemory",
        session_id: str | None = None,
    ):
        self.memory = memory
        self.session_id = session_id

    @property
    def source_name(self) -> str:
        return "L4_semantic"

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """语义检索相关内容"""
        if not query:
            return []

        # 检查是否有向量存储
        if not hasattr(self.memory, "search_l4") or not self.memory._l4_vector_store:
            return []

        # 执行语义检索
        try:
            results = await self.memory.search_l4(
                query=query,
                limit=20,
                min_score=min_relevance,
            )
        except Exception:
            return []

        if not results:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0

        for result in results:
            content = result.get("content", "")
            if not content:
                continue

            # 计算 token
            tokens = self._count_tokens(content, "system", token_counter)

            # 检查预算
            if current_tokens + tokens > token_budget:
                break

            # 优先级基于相似度分数
            score = result.get("score", 0.5)
            priority = min(1.0, max(0.0, score))

            # 过滤低相关性
            if priority < min_relevance:
                continue

            block = ContextBlock(
                content=f"[Semantic Memory] {content}",
                role="system",
                token_count=tokens,
                priority=priority,
                source=self.source_name,
                compressible=True,
                metadata={
                    "score": score,
                    "task_id": result.get("task_id"),
                },
            )

            blocks.append(block)
            current_tokens += tokens

        return blocks
