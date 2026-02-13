"""
UnifiedSearchExecutor - 统一检索执行器

统一路由 + 执行，处理 memory 和 knowledge 两条检索路径。
复用已有的 QueryRewriter + UnifiedReranker。

与 UnifiedRetrievalSource（被动通道）的区别：
- UnifiedRetrievalSource: context building 时自动执行，结果注入上下文
- UnifiedSearchExecutor: Agent 主动调用，结果作为 tool_result 返回
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from loom.context.retrieval.candidates import CandidateOrigin, RetrievalCandidate
from loom.context.retrieval.query_rewriter import QueryRewriter
from loom.context.retrieval.reranker import Reranker

if TYPE_CHECKING:
    from loom.memory.manager import MemoryManager
    from loom.providers.knowledge.base import KnowledgeBaseProvider

logger = logging.getLogger(__name__)


class UnifiedSearchExecutor:
    """
    统一检索工具 query 的执行器。

    职责：
    1. 路由判断：根据 scope 决定搜索范围
    2. 查询增强：复用 QueryRewriter
    3. 并行检索：Memory(L1-L3) + Knowledge(外部知识库)
    4. 统一排序：复用 UnifiedReranker 跨源排序
    5. 结果格式化：返回结构化文本给 Agent
    """

    def __init__(
        self,
        memory: MemoryManager | None = None,
        knowledge_bases: list[KnowledgeBaseProvider] | None = None,
        rewriter: QueryRewriter | None = None,
        reranker: Reranker | None = None,
        default_limit: int = 5,
        min_relevance: float = 0.3,
    ):
        self._memory = memory
        self._kbs = knowledge_bases or []
        self._kb_map = {kb.name: kb for kb in self._kbs}
        self._rewriter = rewriter or QueryRewriter()
        self._reranker = reranker or Reranker()
        self._default_limit = default_limit
        self._min_relevance = min_relevance

    async def execute(
        self,
        query: str,
        scope: str = "auto",
        source: str | None = None,
        intent: str | None = None,
        filters: dict[str, Any] | None = None,
        layer: str = "auto",
        context_messages: list[dict] | None = None,
        session_id: str | None = None,
    ) -> str:
        """执行统一检索，返回格式化结果"""

        # 1. 路由判断
        resolved_scope = self._resolve_scope(scope)

        # 2. 查询增强
        enriched = query
        if intent:
            enriched = f"{query} ({intent})"
        rewrite_result = self._rewriter.rewrite(enriched, context_messages)
        search_query = rewrite_result.rewritten

        # 3. 检索
        candidates: list[RetrievalCandidate] = []

        if resolved_scope in ("memory", "all"):
            memory_candidates = await self._search_memory(
                search_query,
                layer,
                session_id,
            )
            candidates.extend(memory_candidates)

        if resolved_scope in ("knowledge", "all"):
            knowledge_candidates = await self._search_knowledge(
                search_query,
                source,
                filters,
            )
            candidates.extend(knowledge_candidates)

        if not candidates:
            return "未找到相关结果。"

        # 4. 跨源统一排序（多源时）
        if len(candidates) > 1:
            has_mixed_origins = len({c.origin for c in candidates}) > 1
            if has_mixed_origins:
                result = self._reranker.rerank(
                    candidates=candidates,
                    query=query,
                    top_k=self._default_limit,
                )
                candidates = result.candidates
            else:
                # 单源：按 vector_score 降序
                candidates.sort(key=lambda c: c.vector_score, reverse=True)

        # 5. 格式化输出
        return self._format_results(
            candidates[: self._default_limit],
            query,
            resolved_scope,
        )

    def _resolve_scope(self, scope: str) -> str:
        """
        路由策略（极简版）

        设计原则：主动工具由 agent 自主决定搜索范围，
        框架不做语义猜测。
        - 显式 scope → 直接使用
        - auto → 有知识库搜全部，没有只搜记忆
        """
        if scope != "auto":
            return scope
        return "all" if self._kbs else "memory"

    @staticmethod
    def _query_similar(q1: str, q2: str) -> bool:
        """
        判断两个查询是否足够相似（可复用缓存）。

        策略：词集合 Jaccard 相似度 ≥ 0.6，或其中一个是另一个的子集。
        """
        if not q1 or not q2:
            return False

        w1 = {w for w in q1.lower().split() if len(w) >= 2}
        w2 = {w for w in q2.lower().split() if len(w) >= 2}

        if not w1 or not w2:
            return q1.lower().strip() == q2.lower().strip()

        # 子集关系：一个查询完全包含另一个
        if w1 <= w2 or w2 <= w1:
            return True

        # Jaccard 相似度
        intersection = w1 & w2
        union = w1 | w2
        return len(intersection) / len(union) >= 0.6

    async def _search_memory(
        self,
        query: str,
        layer: str,
        session_id: str | None,  # noqa: ARG002
    ) -> list[RetrievalCandidate]:
        """搜索三层记忆"""
        if not self._memory:
            return []

        candidates: list[RetrievalCandidate] = []

        # L1: 最近消息（文本匹配）
        if layer in ("auto", "l1"):
            try:
                messages = self._memory.get_message_items()
                for msg in messages:
                    content = str(msg.content) if msg.content else ""
                    if content and self._text_match(query, content):
                        candidates.append(
                            RetrievalCandidate(
                                id=msg.message_id,
                                content=f"[{msg.role}] {content[:500]}",
                                origin=CandidateOrigin.MEMORY,
                                vector_score=0.5,
                                metadata={"layer": "L1", "role": msg.role},
                            )
                        )
            except Exception:
                logger.debug("L1 search failed", exc_info=True)

        # L2: 工作记忆（文本匹配）
        if layer in ("auto", "l2"):
            try:
                entries = self._memory.get_working_memory(
                    limit=self._default_limit,
                )
                for entry in entries:
                    if entry.content and self._text_match(query, entry.content):
                        candidates.append(
                            RetrievalCandidate(
                                id=entry.entry_id,
                                content=entry.content[:500],
                                origin=CandidateOrigin.MEMORY,
                                vector_score=0.5 + entry.importance * 0.3,
                                metadata={"layer": "L2", "importance": entry.importance},
                            )
                        )
            except Exception:
                logger.debug("L2 search failed", exc_info=True)

        # L3: 持久记忆（语义搜索）
        if layer in ("auto", "l3"):
            try:
                records = await self._memory.search_persistent(
                    query=query,
                    limit=self._default_limit,
                )
                for record in records:
                    candidates.append(
                        RetrievalCandidate(
                            id=record.record_id,
                            content=record.content[:500],
                            origin=CandidateOrigin.L4_SEMANTIC,
                            vector_score=0.7,
                            metadata={"layer": "L3", "importance": record.importance},
                        )
                    )
            except Exception:
                logger.debug("L3 search failed", exc_info=True)

        return candidates

    async def _search_knowledge(
        self,
        query: str,
        source: str | None,
        filters: dict[str, Any] | None,
    ) -> list[RetrievalCandidate]:
        """搜索外部知识库"""
        targets = [self._kb_map[source]] if source and source in self._kb_map else self._kbs

        candidates: list[RetrievalCandidate] = []
        for kb in targets:
            try:
                items = await kb.query(
                    query=query,
                    limit=self._default_limit,
                    filters=filters,
                )
            except Exception:
                logger.debug("Knowledge search failed for %s", kb.name, exc_info=True)
                continue

            for item in items:
                if item.relevance >= self._min_relevance:
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

    def _format_results(
        self,
        candidates: list[RetrievalCandidate],
        query: str,
        scope: str,
    ) -> str:
        """格式化检索结果"""
        scope_label = {
            "memory": "对话记忆",
            "knowledge": "知识库",
            "all": "全部来源",
        }.get(scope, scope)

        lines = [f'搜索 "{query}" ({scope_label}) 找到 {len(candidates)} 条结果：\n']
        for i, c in enumerate(candidates, 1):
            # 来源标签
            if c.origin == CandidateOrigin.MEMORY:
                layer = c.metadata.get("layer", "")
                origin_tag = f"[记忆/{layer}]" if layer else "[记忆]"
            elif c.origin == CandidateOrigin.L4_SEMANTIC:
                origin_tag = "[记忆/L3]"
            elif c.origin == CandidateOrigin.RAG_KNOWLEDGE:
                source_name = c.metadata.get("knowledge_source", "知识库")
                origin_tag = f"[{source_name}]"
            else:
                origin_tag = ""

            score = f"{c.final_score:.2f}" if c.final_score else ""
            lines.append(f"[{i}] {origin_tag} {c.content[:500]}")
            if score:
                lines.append(f"    相关度: {score}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _text_match(query: str, content: str) -> bool:
        """简单文本匹配（L1-L2 降级搜索，CJK-aware）"""
        if not query:
            return True
        query_lower = query.lower()
        content_lower = content.lower()
        # 提取查询 token：空格分词 + CJK bigrams
        tokens: list[str] = [w for w in query_lower.split() if len(w) >= 2]
        cjk_chars = [ch for ch in query_lower if "\u4e00" <= ch <= "\u9fff"]
        for i in range(len(cjk_chars) - 1):
            tokens.append(cjk_chars[i] + cjk_chars[i + 1])
        if len(cjk_chars) == 1:
            tokens.append(cjk_chars[0])
        if not tokens:
            return True
        return any(t in content_lower for t in tokens)
