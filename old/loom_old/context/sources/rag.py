"""
RAG Context Source - 知识库检索源

从外部知识库检索相关知识。
"""

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter
    from loom.providers.knowledge.base import KnowledgeBaseProvider


class RAGKnowledgeSource(ContextSource):
    """
    RAG 知识库源

    从 KnowledgeBaseProvider 检索相关知识。
    优先级基于知识的相关度分数。
    """

    def __init__(
        self,
        knowledge_base: "KnowledgeBaseProvider",
        relevance_threshold: float = 0.7,
    ):
        """
        初始化 RAG 源

        Args:
            knowledge_base: 知识库提供者
            relevance_threshold: 相关度阈值
        """
        self.knowledge_base = knowledge_base
        self.relevance_threshold = relevance_threshold

    @property
    def source_name(self) -> str:
        return "RAG_knowledge"

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """从知识库检索相关知识"""
        if not query:
            return []

        # 使用更严格的阈值
        threshold = max(min_relevance, self.relevance_threshold)

        # 查询知识库
        try:
            items = await self.knowledge_base.query(query=query, limit=20)
        except Exception:
            return []

        if not items:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0

        for item in items:
            # 过滤低相关性
            if item.relevance < threshold:
                continue

            content = f"[Knowledge: {item.source}] {item.content}"

            # 计算 token
            tokens = self._count_tokens(content, "system", token_counter)

            # 检查预算
            if current_tokens + tokens > token_budget:
                break

            block = ContextBlock(
                content=content,
                role="system",
                token_count=tokens,
                priority=item.relevance,
                source=self.source_name,
                compressible=True,
                metadata={
                    "knowledge_id": item.id,
                    "knowledge_source": item.source,
                    "relevance": item.relevance,
                },
            )

            blocks.append(block)
            current_tokens += tokens

        return blocks
