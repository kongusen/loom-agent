"""
Reranker - 跨源重排序 + 去重

对来自 L4、RAG 和 Memory 的候选项进行统一的多信号加权排序，
并通过内容指纹去重，避免重复内容占用预算。

这是系统唯一的重排序器，统一处理所有检索源的候选项。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from loom.context.retrieval.candidates import RetrievalCandidate


@dataclass
class RerankResult:
    """重排序结果"""

    candidates: list[RetrievalCandidate]
    total_recalled: int = 0
    duplicates_removed: int = 0
    elapsed_ms: float = 0.0

    @property
    def top(self) -> RetrievalCandidate | None:
        return self.candidates[0] if self.candidates else None


# ============ 重排序信号 ============


class RerankSignal(ABC):
    """重排序信号基类"""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def weight(self) -> float: ...

    @abstractmethod
    def score(self, candidate: RetrievalCandidate, context: dict[str, Any]) -> float:
        """计算信号分数 (0.0 - 1.0)"""
        ...


class VectorScoreSignal(RerankSignal):
    """向量/相关度分数（直接使用召回分数）"""

    @property
    def name(self) -> str:
        return "vector_score"

    @property
    def weight(self) -> float:
        return 0.40

    def score(self, candidate: RetrievalCandidate, _context: dict[str, Any]) -> float:
        return max(0.0, min(1.0, candidate.vector_score))


class ContentLengthSignal(RerankSignal):
    """
    内容长度信号

    适中长度的内容信息密度更高。
    太短（< 50 字符）信息不足，太长（> 2000 字符）效率低。
    """

    @property
    def name(self) -> str:
        return "content_length"

    @property
    def weight(self) -> float:
        return 0.10

    def score(self, candidate: RetrievalCandidate, _context: dict[str, Any]) -> float:
        length = len(candidate.content)
        if length < 50:
            return 0.3
        if length > 2000:
            return 0.5
        # 200-800 字符是最佳区间
        if 200 <= length <= 800:
            return 1.0
        if length < 200:
            return 0.3 + 0.7 * (length - 50) / 150
        # 800-2000
        return 1.0 - 0.5 * (length - 800) / 1200


class OriginDiversitySignal(RerankSignal):
    """
    来源多样性信号

    鼓励结果来自不同来源，避免单一来源主导。
    通过 context 中的已选来源分布来计算。
    """

    @property
    def name(self) -> str:
        return "origin_diversity"

    @property
    def weight(self) -> float:
        return 0.15

    def score(self, candidate: RetrievalCandidate, context: dict[str, Any]) -> float:
        origin_counts: dict[str, int] = context.get("_origin_counts", {})
        if not origin_counts:
            return 0.8
        origin_key = candidate.origin.value
        count = origin_counts.get(origin_key, 0)
        total = sum(origin_counts.values())
        if total == 0:
            return 0.8
        ratio = count / total
        # 如果某来源已经占比过高，降低其新候选的分数
        if ratio > 0.7:
            return 0.3
        if ratio > 0.5:
            return 0.6
        return 0.9


class QueryOverlapSignal(RerankSignal):
    """
    查询词重叠信号

    候选内容中包含查询关键词越多，相关性越高。
    """

    @property
    def name(self) -> str:
        return "query_overlap"

    @property
    def weight(self) -> float:
        return 0.35

    def score(self, candidate: RetrievalCandidate, context: dict[str, Any]) -> float:
        query: str = context.get("query", "")
        if not query:
            return 0.5

        query_words = set(query.lower().split())
        # 过滤短词
        query_words = {w for w in query_words if len(w) >= 2}
        if not query_words:
            return 0.5

        content_lower = candidate.content.lower()
        matched = sum(1 for w in query_words if w in content_lower)
        return min(1.0, matched / len(query_words))


# ============ 默认信号集 ============

DEFAULT_SIGNALS: list[RerankSignal] = [
    VectorScoreSignal(),
    QueryOverlapSignal(),
    OriginDiversitySignal(),
    ContentLengthSignal(),
]


# ============ 主重排序器 ============


class Reranker:
    """
    统一重排序器

    系统唯一的重排序器，处理所有检索源的候选项：
    1. 去重：基于内容指纹合并重复候选（保留高分）
    2. 多信号加权排序
    3. 过滤低分候选
    """

    def __init__(
        self,
        signals: list[RerankSignal] | None = None,
        min_score_threshold: float = 0.1,
        dedup: bool = True,
    ):
        self.signals = signals or list(DEFAULT_SIGNALS)
        self.min_score_threshold = min_score_threshold
        self.dedup = dedup

    def rerank(
        self,
        candidates: list[RetrievalCandidate],
        query: str = "",
        top_k: int = 10,
    ) -> RerankResult:
        """
        对候选项进行统一重排序

        Args:
            candidates: 来自多个源的候选项
            query: 原始查询（用于 query overlap 信号）
            top_k: 最终返回数量
        """
        start = time.monotonic()
        total_recalled = len(candidates)

        # 1. 去重
        duplicates_removed = 0
        if self.dedup:
            candidates, duplicates_removed = self._deduplicate(candidates)

        # 2. 多信号加权排序
        total_weight = sum(s.weight for s in self.signals)
        if total_weight <= 0:
            total_weight = 1.0

        # 构建来源分布（用于 diversity 信号）
        origin_counts: dict[str, int] = {}
        for c in candidates:
            key = c.origin.value
            origin_counts[key] = origin_counts.get(key, 0) + 1

        ctx: dict[str, Any] = {
            "query": query,
            "_origin_counts": origin_counts,
        }

        for candidate in candidates:
            weighted_sum = 0.0
            for signal in self.signals:
                s = signal.score(candidate, ctx)
                candidate.signal_scores[signal.name] = s
                weighted_sum += s * signal.weight
            candidate.final_score = weighted_sum / total_weight

        # 3. 过滤 + 排序
        candidates = [c for c in candidates if c.final_score >= self.min_score_threshold]
        candidates.sort(key=lambda c: c.final_score, reverse=True)

        elapsed = (time.monotonic() - start) * 1000
        return RerankResult(
            candidates=candidates[:top_k],
            total_recalled=total_recalled,
            duplicates_removed=duplicates_removed,
            elapsed_ms=round(elapsed, 2),
        )

    @staticmethod
    def _deduplicate(
        candidates: list[RetrievalCandidate],
    ) -> tuple[list[RetrievalCandidate], int]:
        """基于内容指纹去重，保留 vector_score 更高的"""
        seen: dict[str, RetrievalCandidate] = {}
        removed = 0
        for c in candidates:
            fp = c.fingerprint
            if fp in seen:
                # 保留分数更高的
                if c.vector_score > seen[fp].vector_score:
                    seen[fp] = c
                removed += 1
            else:
                seen[fp] = c
        return list(seen.values()), removed
