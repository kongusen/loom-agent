"""CompressionScorer — 三层压缩评分（公理一）"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import EmbeddingProvider, Message


class CompressionScorer:
    """三层压缩评分：score(h) = K(h) · rel(h, goal) · w(h)"""

    def __init__(self, embedding: EmbeddingProvider | None = None, lambda_decay: float = 0.1):
        self.embedding = embedding
        self.lambda_decay = lambda_decay

    async def score_history(
        self, history: list[Message], goal: str, current_time: float | None = None
    ) -> list[tuple[Message, float]]:
        """对历史消息打分"""
        if current_time is None:
            current_time = time.time()

        scored = []
        for idx, msg in enumerate(history):
            k = self._kernel_score(msg)
            if k == 0:
                scored.append((msg, 0.0))
                continue

            rel = await self._relevance_score(msg, goal)
            # 使用索引作为 age 的近似
            age = len(history) - idx
            w = math.exp(-self.lambda_decay * age)

            scored.append((msg, k * rel * w))

        return scored

    async def score_history_batch(
        self, history: list[Message], goal: str, current_time: float | None = None
    ) -> list[tuple[Message, float]]:
        """P2: 批量 embedding - 减少 API 调用."""
        if not self.embedding:
            return await self.score_history(history, goal, current_time)

        if current_time is None:
            current_time = time.time()

        # 批量提取文本
        texts = [msg.content if isinstance(msg.content, str) else str(msg.content) for msg in history]
        texts.append(goal)

        # 一次性 embed
        embeddings = await self._embed_batch(texts)
        goal_emb = embeddings[-1]

        scored = []
        for idx, msg in enumerate(history):
            k = self._kernel_score(msg)
            if k == 0:
                scored.append((msg, 0.0))
                continue

            # 使用批量 embedding
            similarity = self._cosine_similarity(embeddings[idx], goal_emb)
            age = len(history) - idx
            w = math.exp(-self.lambda_decay * age)

            scored.append((msg, k * similarity * w))

        return scored

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量 embedding."""
        if hasattr(self.embedding, "embed_batch"):
            return await self.embedding.embed_batch(texts)
        # 回退到逐个调用
        return [await self.embedding.embed(text) for text in texts]

    def _kernel_score(self, msg: Message) -> int:
        """层A：结构护栏（0 或 1）"""
        # 简化：assistant 消息保留，其他根据内容判断
        if hasattr(msg, 'role'):
            if msg.role == "assistant":
                return 1
            if msg.role == "tool":
                return 1
        return 1

    async def _relevance_score(self, msg: Message, goal: str) -> float:
        """层B：目标锚定（embedding 相似度）"""
        if not self.embedding:
            return 0.5

        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        msg_emb = await self.embedding.embed(content)
        goal_emb = await self.embedding.embed(goal)
        return self._cosine_similarity(msg_emb, goal_emb)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
