"""
RetrievalInjector - 预算感知注入器

将重排序后的候选项转换为 ContextBlock，
根据分数决定注入优先级：
- score ≥ promote_threshold → L2 工作集优先级 (0.75)
- score < promote_threshold → 背景优先级 (0.35)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.retrieval.candidates import CandidateOrigin, RetrievalCandidate

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class RetrievalInjector:
    """
    检索结果注入器

    职责：
    1. 将 RetrievalCandidate 转换为 ContextBlock
    2. 根据 final_score 分配优先级
    3. 严格遵守 token 预算
    """

    def __init__(
        self,
        promote_threshold: float = 0.7,
        high_priority: float = 0.75,
        low_priority: float = 0.35,
    ):
        """
        Args:
            promote_threshold: 提升阈值，≥ 此分数的候选获得高优先级
            high_priority: 高分候选的 ContextBlock 优先级
            low_priority: 低分候选的 ContextBlock 优先级
        """
        self.promote_threshold = promote_threshold
        self.high_priority = high_priority
        self.low_priority = low_priority

    def inject(
        self,
        candidates: list[RetrievalCandidate],
        token_budget: int,
        token_counter: TokenCounter,
    ) -> list[ContextBlock]:
        """
        将候选项注入为 ContextBlock

        Args:
            candidates: 已排序的候选项（高分在前）
            token_budget: 可用 token 预算
            token_counter: Token 计数器

        Returns:
            ContextBlock 列表，总 token 不超过 token_budget
        """
        blocks: list[ContextBlock] = []
        used_tokens = 0

        for candidate in candidates:
            if used_tokens >= token_budget:
                break

            # 构建内容（带来源标签）
            content = self._format_content(candidate)

            # 计算 token
            tokens = token_counter.count_messages(
                [{"role": "system", "content": content}]
            )

            if used_tokens + tokens > token_budget:
                continue  # 跳过超预算的，尝试下一个更短的

            # 根据分数决定优先级
            priority = (
                self.high_priority
                if candidate.final_score >= self.promote_threshold
                else self.low_priority
            )

            block = ContextBlock(
                content=content,
                role="system",
                token_count=tokens,
                priority=priority,
                source="retrieval",
                compressible=True,
                metadata={
                    "candidate_id": candidate.id,
                    "origin": candidate.origin.value,
                    "final_score": round(candidate.final_score, 4),
                    "vector_score": round(candidate.vector_score, 4),
                    "promoted": candidate.final_score >= self.promote_threshold,
                },
            )

            blocks.append(block)
            used_tokens += tokens

        return blocks

    @staticmethod
    def _format_content(candidate: RetrievalCandidate) -> str:
        """格式化候选内容，添加来源标签"""
        if candidate.origin == CandidateOrigin.RAG_KNOWLEDGE:
            source = candidate.metadata.get("knowledge_source", "knowledge")
            return f"[Knowledge: {source}] {candidate.content}"
        return f"[Retrieved Memory] {candidate.content}"
