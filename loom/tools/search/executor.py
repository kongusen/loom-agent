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
from loom.events.actions import KnowledgeAction

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
    3. 并行检索：Memory(L1-L4) + Knowledge(外部知识库)
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

        # 0. Session 级 L1 缓存检查（同 session 近期相似查询复用）
        if session_id and self._memory:
            cached = self._check_l1_cache(query, session_id)
            if cached:
                logger.debug("L1 cache hit for query=%r session=%s", query, session_id)
                return cached

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
                search_query, layer, session_id,
            )
            candidates.extend(memory_candidates)

        if resolved_scope in ("knowledge", "all"):
            knowledge_candidates = await self._search_knowledge(
                search_query, source, filters,
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
            candidates[:self._default_limit], query, resolved_scope,
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

    def _check_l1_cache(self, query: str, session_id: str) -> str | None:
        """
        从 L1 中查找同 session 的近期搜索结果。

        遍历 L1 中 action == KnowledgeAction.SEARCH_RESULT 的 Task，
        如果 query 相似则直接返回缓存的 formatted_output。
        """
        if not self._memory:
            return None
        try:
            recent_tasks = self._memory.get_l1_tasks(
                limit=20, session_id=session_id,
            )
        except Exception:
            logger.debug("L1 cache check failed", exc_info=True)
            return None

        for task in reversed(recent_tasks):
            if (task.action == KnowledgeAction.SEARCH_RESULT
                    and self._query_similar(
                        task.parameters.get("query", ""), query)):
                output = None
                if isinstance(task.result, dict):
                    output = task.result.get("formatted_output")
                if output:
                    return str(output)
        return None

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
        self, query: str, layer: str, session_id: str | None,
    ) -> list[RetrievalCandidate]:
        """搜索 L1-L4 记忆层"""
        if not self._memory:
            return []

        candidates: list[RetrievalCandidate] = []

        # L1: 最近任务
        if layer in ("auto", "l1"):
            try:
                tasks = self._memory.get_l1_tasks(
                    limit=self._default_limit, session_id=session_id,
                )
                for t in tasks:
                    content = self._task_to_content(t)
                    if content and self._text_match(query, content):
                        candidates.append(RetrievalCandidate(
                            id=t.taskId,
                            content=content,
                            origin=CandidateOrigin.MEMORY,
                            vector_score=0.5,
                            metadata={"layer": "L1", "action": t.action},
                        ))
            except Exception:
                logger.debug("L1 search failed", exc_info=True)

        # L2: 重要任务
        if layer in ("auto", "l2"):
            try:
                tasks = self._memory.get_l2_tasks(
                    limit=self._default_limit, session_id=session_id,
                )
                for t in tasks:
                    content = self._task_to_content(t)
                    if content and self._text_match(query, content):
                        importance = t.metadata.get("importance", 0.5) if t.metadata else 0.5
                        candidates.append(RetrievalCandidate(
                            id=t.taskId,
                            content=content,
                            origin=CandidateOrigin.MEMORY,
                            vector_score=0.5 + importance * 0.3,
                            metadata={"layer": "L2", "importance": importance},
                        ))
            except Exception:
                logger.debug("L2 search failed", exc_info=True)

        # L3: 历史摘要
        if layer in ("auto", "l3"):
            try:
                loom = self._memory._loom_memory
                summaries = loom.get_l3_summaries(
                    limit=self._default_limit, session_id=session_id,
                )
                for s in summaries:
                    content = f"{s.action}: {s.param_summary} -> {s.result_summary}"
                    if self._text_match(query, content):
                        candidates.append(RetrievalCandidate(
                            id=s.task_id,
                            content=content,
                            origin=CandidateOrigin.MEMORY,
                            vector_score=0.4,
                            metadata={"layer": "L3"},
                        ))
            except Exception:
                logger.debug("L3 search failed", exc_info=True)

        # L4: 向量语义检索
        if layer in ("auto", "l4"):
            try:
                loom = self._memory._loom_memory
                l4_tasks = await loom.search_tasks(
                    query=query,
                    limit=self._default_limit,
                    session_id=session_id,
                )

                for t in l4_tasks:
                    content = self._task_to_content(t)
                    if content:
                        candidates.append(RetrievalCandidate(
                            id=t.taskId,
                            content=content,
                            origin=CandidateOrigin.L4_SEMANTIC,
                            vector_score=0.7,
                            metadata={"layer": "L4"},
                        ))
            except Exception:
                logger.debug("L4 search failed", exc_info=True)

        return candidates

    async def _search_knowledge(
        self,
        query: str,
        source: str | None,
        filters: dict[str, Any] | None,
    ) -> list[RetrievalCandidate]:
        """搜索外部知识库"""
        targets = (
            [self._kb_map[source]] if source and source in self._kb_map
            else self._kbs
        )

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
                origin_tag = "[记忆/L4]"
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
    def _task_to_content(task: Any) -> str:
        """将 Task 转换为可读文本"""
        parts: list[str] = []
        if task.action:
            parts.append(str(task.action))
        params = task.parameters
        if isinstance(params, dict):
            content = params.get("content", "")
            if content:
                parts.append(str(content)[:200])
            elif params:
                parts.append(str(params)[:200])
        elif params:
            parts.append(str(params)[:200])
        result = task.result
        if isinstance(result, dict):
            r_content = result.get("content", "") or result.get("message", "")
            if r_content:
                parts.append(f"-> {str(r_content)[:200]}")
        elif result:
            parts.append(f"-> {str(result)[:200]}")
        return ": ".join(parts) if parts else ""

    @staticmethod
    def _text_match(query: str, content: str) -> bool:
        """简单文本匹配（L1-L3 降级搜索）"""
        if not query:
            return True
        query_lower = query.lower()
        content_lower = content.lower()
        # 任意一个查询词出现即匹配
        words = [w for w in query_lower.split() if len(w) >= 2]
        if not words:
            return True
        return any(w in content_lower for w in words)
