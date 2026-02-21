"""
UnifiedRetrievalSource - 统一检索上下文源

替代 L4SemanticSource 和 RAGKnowledgeSource，
将两条独立管道合并为一条统一的检索管道：

Query → QueryRewriter → Parallel Retrieval → UnifiedReranker → RetrievalInjector → ContextBlocks
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.retrieval.candidates import RetrievalCandidate
from loom.context.retrieval.injector import RetrievalInjector
from loom.context.retrieval.query_rewriter import QueryRewriter
from loom.context.retrieval.reranker import Reranker
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory
    from loom.memory.tokenizer import TokenCounter
    from loom.providers.knowledge.base import KnowledgeBaseProvider

logger = logging.getLogger(__name__)


class UnifiedRetrievalSource(ContextSource):
    """
    统一检索源

    整合 L4 语义检索和 RAG 知识库检索为单一 ContextSource。
    两个后端在共享的 retrieval 预算池中竞争，由 Reranker 统一排序。

    用法：
        source = UnifiedRetrievalSource(
            memory=loom_memory,
            knowledge_bases=[my_rag_provider],
        )
        blocks = await source.collect(query, token_budget, counter)
    """

    def __init__(
        self,
        memory: LoomMemory | None = None,
        knowledge_bases: list[KnowledgeBaseProvider] | None = None,
        rewriter: QueryRewriter | None = None,
        reranker: Reranker | None = None,
        injector: RetrievalInjector | None = None,
        recall_limit: int = 20,
        context_messages: list[dict[str, str]] | None = None,
    ):
        """
        Args:
            memory: LoomMemory 实例（提供 L4 语义检索）
            knowledge_bases: 知识库提供者列表（提供 RAG 检索）
            rewriter: 查询重写器（默认创建）
            reranker: 统一重排序器（默认创建）
            injector: 检索注入器（默认创建）
            recall_limit: 每个后端的召回数量上限
            context_messages: 对话上下文（用于查询重写）
        """
        self._memory = memory
        self._knowledge_bases = knowledge_bases or []
        self._rewriter = rewriter or QueryRewriter()
        self._reranker = reranker or Reranker()
        self._injector = injector or RetrievalInjector()
        self._recall_limit = recall_limit
        self._context_messages = context_messages

    @property
    def source_name(self) -> str:
        return "retrieval"

    def set_context_messages(self, messages: list[dict[str, str]]) -> None:
        """更新对话上下文（每次迭代前调用）"""
        self._context_messages = messages

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: TokenCounter,
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """统一检索并注入上下文"""
        if not query:
            return []

        if not self._memory and not self._knowledge_bases:
            return []

        # 1. 查询重写
        rewrite_result = self._rewriter.rewrite(query, self._context_messages)
        enriched_query = rewrite_result.rewritten

        # 2. 并行召回
        candidates: list[RetrievalCandidate] = []

        # L4 语义检索
        l4_candidates = await self._recall_l4(enriched_query, min_relevance)
        candidates.extend(l4_candidates)

        # RAG 知识库检索
        rag_candidates = await self._recall_rag(enriched_query, min_relevance)
        candidates.extend(rag_candidates)

        if not candidates:
            return []

        # 3. 统一重排序 + 去重
        rerank_result = self._reranker.rerank(
            candidates=candidates,
            query=query,  # 用原始查询做 overlap 计算
            top_k=self._recall_limit,
        )

        if not rerank_result.candidates:
            return []

        logger.debug(
            "Unified retrieval: recalled=%d, deduped=%d, reranked=%d (%.1fms)",
            rerank_result.total_recalled,
            rerank_result.duplicates_removed,
            len(rerank_result.candidates),
            rerank_result.elapsed_ms,
        )

        # 4. 预算感知注入
        return self._injector.inject(
            candidates=rerank_result.candidates,
            token_budget=token_budget,
            token_counter=token_counter,
        )

    async def _recall_l4(
        self,
        query: str,
        min_relevance: float,
    ) -> list[RetrievalCandidate]:
        """从 L4 向量存储召回"""
        if not self._memory:
            return []

        # L4 向量存储功能已移除，使用 L3 持久记忆代替
        if not hasattr(self._memory, "search_l3"):
            return []

        try:
            # 使用 L3 持久记忆检索代替 L4
            if not hasattr(self._memory, "search_l3"):
                return []
            results = await self._memory.search_l3(  # type: ignore[attr-defined]
                query=query,
                limit=self._recall_limit,
                min_score=min_relevance,
            )
        except Exception:
            logger.debug("L4 recall failed", exc_info=True)
            return []

        candidates = []
        for r in results:
            content = r.get("content", "")
            if not content:
                continue
            candidates.append(
                RetrievalCandidate.from_memory_result(
                    content=content,
                    score=r.get("score", 0.0),
                    memory_id=r.get("id", ""),
                    metadata={k: v for k, v in r.items() if k not in ("content", "score", "id")},
                )
            )
        return candidates

    async def _recall_rag(
        self,
        query: str,
        min_relevance: float,
    ) -> list[RetrievalCandidate]:
        """从 RAG 知识库召回"""
        candidates: list[RetrievalCandidate] = []

        for kb in self._knowledge_bases:
            try:
                items = await kb.query(query=query, limit=self._recall_limit)
            except Exception:
                logger.debug("RAG recall failed for %s", type(kb).__name__, exc_info=True)
                continue

            for item in items:
                if item.relevance < min_relevance:
                    continue
                candidates.append(
                    RetrievalCandidate.from_knowledge_item(
                        item_id=item.id,
                        content=item.content,
                        source=item.source,
                        relevance=item.relevance,
                        metadata=item.metadata,
                    )
                )

        return candidates
