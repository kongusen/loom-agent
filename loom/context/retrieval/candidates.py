"""
RetrievalCandidate - 统一检索候选项

将 MemoryUnit 和 KnowledgeItem 包装为统一的候选项，
供 Reranker 进行跨源排序和去重。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CandidateOrigin(Enum):
    """候选项来源"""
    L4_SEMANTIC = "l4_semantic"
    RAG_KNOWLEDGE = "rag_knowledge"
    MEMORY = "memory"  # L1-L3 记忆结果（主动检索通道）


@dataclass
class RetrievalCandidate:
    """
    统一检索候选项

    无论来自 L4 向量检索还是 RAG 知识库，
    都归一化为相同的结构参与重排序。
    """

    id: str
    content: str
    origin: CandidateOrigin
    vector_score: float = 0.0

    # 重排序后的最终分数
    final_score: float = 0.0
    signal_scores: dict[str, float] = field(default_factory=dict)

    # 元数据（保留原始来源信息）
    metadata: dict[str, Any] = field(default_factory=dict)

    # 用于去重的内容指纹
    _fingerprint: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self._fingerprint:
            self._fingerprint = self._compute_fingerprint(self.content)

    @staticmethod
    def _compute_fingerprint(text: str) -> str:
        """计算内容指纹（用于去重）"""
        normalized = " ".join(text.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    @classmethod
    def from_memory_result(
        cls,
        content: str,
        score: float,
        memory_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> RetrievalCandidate:
        """从 L4 语义检索结果构建"""
        return cls(
            id=memory_id or f"l4_{hashlib.md5(content.encode()).hexdigest()[:8]}",
            content=content,
            origin=CandidateOrigin.L4_SEMANTIC,
            vector_score=score,
            metadata=metadata or {},
        )

    @classmethod
    def from_knowledge_item(
        cls,
        item_id: str,
        content: str,
        source: str,
        relevance: float,
        metadata: dict[str, Any] | None = None,
    ) -> RetrievalCandidate:
        """从 KnowledgeItem 构建"""
        meta = metadata or {}
        meta["knowledge_source"] = source
        return cls(
            id=item_id,
            content=content,
            origin=CandidateOrigin.RAG_KNOWLEDGE,
            vector_score=relevance,
            metadata=meta,
        )
