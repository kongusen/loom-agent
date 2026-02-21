"""
Memory Reranker - 两阶段检索重排序

解决 L4 语义检索中向量相似度 ≠ 任务相关性的问题。

两阶段策略：
1. 向量召回（Recall）：快速从向量库中召回 top-N 候选
2. 精排（Rerank）：基于多维信号对候选进行重排序

多维信号：
- 向量相似度（基础分）
- 时间衰减（近期记忆优先）
- 访问频率（高频使用的记忆更重要）
- 信息密度（token 效率）
- 任务相关性（与当前任务的语义匹配）
"""

from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loom.memory.types import WorkingMemoryEntry
from loom.memory.vector_store import VectorSearchResult

# MemoryUnit 类型已移除，使用 WorkingMemoryEntry 代替
MemoryUnit = WorkingMemoryEntry  # type: ignore[misc]


@dataclass
class RerankCandidate:
    """重排序候选项"""

    memory: MemoryUnit
    vector_score: float = 0.0
    rerank_score: float = 0.0
    signal_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class RerankResult:
    """重排序结果"""

    candidates: list[RerankCandidate]
    recall_count: int = 0
    rerank_count: int = 0
    elapsed_ms: float = 0.0

    @property
    def top(self) -> MemoryUnit | None:
        return self.candidates[0].memory if self.candidates else None

    @property
    def memories(self) -> list[MemoryUnit]:
        return [c.memory for c in self.candidates]


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
    def score(self, candidate: RerankCandidate, context: dict[str, Any]) -> float:
        """计算信号分数 (0.0 - 1.0)"""
        ...


class VectorSimilaritySignal(RerankSignal):
    """向量相似度信号（直接使用召回分数）"""

    @property
    def name(self) -> str:
        return "vector_similarity"

    @property
    def weight(self) -> float:
        return 0.30

    def score(self, candidate: RerankCandidate, _context: dict[str, Any]) -> float:
        return max(0.0, min(1.0, candidate.vector_score))


class TimeDecaySignal(RerankSignal):
    """
    时间衰减信号

    使用指数衰减：score = exp(-λ * hours_ago)
    半衰期默认 48 小时（2天前的记忆分数降为 0.5）
    """

    def __init__(self, half_life_hours: float = 48.0):
        self._lambda = math.log(2) / half_life_hours

    @property
    def name(self) -> str:
        return "time_decay"

    @property
    def weight(self) -> float:
        return 0.20

    def score(self, candidate: RerankCandidate, _context: dict[str, Any]) -> float:
        created = candidate.memory.created_at
        hours_ago = (time.time() - created.timestamp()) / 3600.0
        if hours_ago < 0:
            hours_ago = 0
        return math.exp(-self._lambda * hours_ago)


class AccessFrequencySignal(RerankSignal):
    """
    访问频率信号

    高频访问的记忆更可能是重要的。
    使用对数缩放避免极端值主导。
    """

    @property
    def name(self) -> str:
        return "access_frequency"

    @property
    def weight(self) -> float:
        return 0.15

    def score(self, candidate: RerankCandidate, _context: dict[str, Any]) -> float:
        access_count = candidate.memory.metadata.get("access_count", 0)
        if access_count <= 0:
            return 0.1
        # log1p 缩放：1次→0.69, 10次→0.96, 100次→1.0
        return min(1.0, math.log1p(access_count) / math.log1p(100))


class InformationDensitySignal(RerankSignal):
    """信息密度信号（token 效率）"""

    @property
    def name(self) -> str:
        return "information_density"

    @property
    def weight(self) -> float:
        return 0.15

    def score(self, candidate: RerankCandidate, _context: dict[str, Any]) -> float:
        # information_density 属性可能不存在，使用默认值
        density = getattr(candidate.memory, "information_density", 0.5)
        result: float = max(0.0, min(1.0, density))
        return result


class ImportanceSignal(RerankSignal):
    """记忆重要性信号（直接使用 MemoryUnit.importance）"""

    @property
    def name(self) -> str:
        return "importance"

    @property
    def weight(self) -> float:
        return 0.20

    def score(self, candidate: RerankCandidate, _context: dict[str, Any]) -> float:
        result: float = max(0.0, min(1.0, candidate.memory.importance))
        return result


# ============ 主重排序器 ============


DEFAULT_SIGNALS: list[RerankSignal] = [
    VectorSimilaritySignal(),
    TimeDecaySignal(),
    AccessFrequencySignal(),
    InformationDensitySignal(),
    ImportanceSignal(),
]


class MemoryReranker:
    """
    记忆重排序器

    两阶段检索：
    1. 向量召回 top-N 候选（由外部调用方完成）
    2. 多信号加权重排序

    用法：
        reranker = MemoryReranker()
        result = reranker.rerank(candidates, recall_results, context={"query": "..."})
        top_memories = result.memories[:5]
    """

    def __init__(
        self,
        signals: list[RerankSignal] | None = None,
        recall_multiplier: int = 3,
        min_score_threshold: float = 0.1,
    ):
        """
        Args:
            signals: 重排序信号列表（默认使用 DEFAULT_SIGNALS）
            recall_multiplier: 召回倍数（最终需要 K 条，召回 K * multiplier 条）
            min_score_threshold: 最低分数阈值，低于此分数的候选被过滤
        """
        self.signals = signals or list(DEFAULT_SIGNALS)
        self.recall_multiplier = recall_multiplier
        self.min_score_threshold = min_score_threshold

    @property
    def recall_top_k(self) -> int:
        """建议的召回数量（基于 recall_multiplier）"""
        return self.recall_multiplier

    def suggest_recall_k(self, final_k: int) -> int:
        """根据最终需要的数量，计算建议的召回数量"""
        return final_k * self.recall_multiplier

    def rerank(
        self,
        memories: list[MemoryUnit],
        recall_results: list[VectorSearchResult],
        context: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> RerankResult:
        """
        对召回的记忆进行重排序

        Args:
            memories: 召回的 MemoryUnit 列表
            recall_results: 向量搜索结果（提供 vector_score）
            context: 查询上下文（query, task_type 等）
            top_k: 最终返回数量

        Returns:
            RerankResult
        """
        start = time.monotonic()
        ctx = context or {}

        # 构建 id → vector_score 映射
        score_map: dict[str, float] = {r.id: r.score for r in recall_results}

        # 构建候选列表
        candidates = [
            RerankCandidate(
                memory=mem,
                vector_score=score_map.get(getattr(mem, "entry_id", ""), 0.0),  # type: ignore[attr-defined]
            )
            for mem in memories
        ]

        # 计算每个候选的加权分数
        total_weight = sum(s.weight for s in self.signals)
        if total_weight <= 0:
            total_weight = 1.0

        for candidate in candidates:
            weighted_sum = 0.0
            for signal in self.signals:
                s = signal.score(candidate, ctx)
                candidate.signal_scores[signal.name] = s
                weighted_sum += s * signal.weight
            candidate.rerank_score = weighted_sum / total_weight

        # 过滤低分候选
        candidates = [c for c in candidates if c.rerank_score >= self.min_score_threshold]

        # 按 rerank_score 降序排序
        candidates.sort(key=lambda c: c.rerank_score, reverse=True)

        elapsed = (time.monotonic() - start) * 1000
        return RerankResult(
            candidates=candidates[:top_k],
            recall_count=len(memories),
            rerank_count=len(candidates),
            elapsed_ms=round(elapsed, 2),
        )
