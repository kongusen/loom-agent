"""
Memory Store — L3 持久记忆的可插拔存储后端

提供 Protocol 接口，允许应用层选择存储实现：
- InMemoryStore: 内存实现（测试/快速开始）
- 应用层可实现: SQLiteStore, RedisStore, PgVectorStore 等

符合 Loom 框架原则：框架提供机制，应用选择策略
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import MemoryRecord


def _tokenize(text: str) -> set[str]:
    """CJK-aware tokenization: bigrams + unigrams for CJK, words for Latin."""
    tokens: set[str] = set()
    cjk_chars: list[str] = []
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            cjk_chars.append(ch)
    # CJK unigrams + bigrams
    for ch in cjk_chars:
        tokens.add(ch)
    for i in range(len(cjk_chars) - 1):
        tokens.add(cjk_chars[i] + cjk_chars[i + 1])
    # Latin / space-separated words
    for w in text.split():
        if len(w) >= 2 and not all("\u4e00" <= c <= "\u9fff" for c in w):
            tokens.add(w)
    return tokens


@runtime_checkable
class MemoryStore(Protocol):
    """
    L3 持久记忆存储接口

    所有 L3 后端必须实现此 Protocol。
    支持文本查询和向量查询两种检索方式。

    实现示例：
    - InMemoryStore（内存，用于测试）
    - SQLiteStore（本地持久化）
    - PgVectorStore（PostgreSQL + pgvector，生产环境）
    - RedisStore（Redis，高性能缓存）
    """

    async def save(self, record: MemoryRecord) -> str:
        """
        保存记忆记录

        Args:
            record: 要保存的记录

        Returns:
            记录 ID
        """
        ...

    async def query_by_text(
        self,
        query: str,
        limit: int = 5,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[MemoryRecord]:
        """
        文本查询（简单匹配）

        Args:
            query: 查询文本
            limit: 最大返回数
            user_id: 用户过滤
            session_id: session 过滤

        Returns:
            匹配的记录列表
        """
        ...

    async def query_by_vector(
        self,
        embedding: list[float],
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[MemoryRecord]:
        """
        向量查询（语义检索）

        Args:
            embedding: 查询向量
            limit: 最大返回数
            user_id: 用户过滤

        Returns:
            匹配的记录列表（按相似度排序）
        """
        ...

    async def delete(self, record_id: str) -> bool:
        """
        删除记录

        Args:
            record_id: 记录 ID

        Returns:
            是否成功删除
        """
        ...

    async def list_by_session(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """
        按 session 列出记录

        Args:
            session_id: session ID
            limit: 最大返回数

        Returns:
            该 session 的记录列表
        """
        ...

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """
        按用户列出记录

        Args:
            user_id: 用户 ID
            limit: 最大返回数

        Returns:
            该用户的记录列表
        """
        ...


class InMemoryStore:
    """
    内存实现的 MemoryStore（参考实现）

    用于测试和快速开始。生产环境建议使用持久化存储。

    特性：
    - 简单的字典存储
    - 文本匹配查询（大小写不敏感）
    - 余弦相似度向量查询
    - FIFO 容量限制
    """

    def __init__(self, max_records: int = 10000):
        self._records: dict[str, MemoryRecord] = {}
        self.max_records = max_records

    async def save(self, record: MemoryRecord) -> str:
        self._records[record.record_id] = record

        # FIFO 容量限制
        if len(self._records) > self.max_records:
            oldest_id = min(
                self._records,
                key=lambda rid: self._records[rid].created_at,
            )
            del self._records[oldest_id]

        return record.record_id

    async def query_by_text(
        self,
        query: str,
        limit: int = 5,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[MemoryRecord]:
        query_lower = query.lower()
        matches: list[tuple[float, MemoryRecord]] = []

        for record in self._records.values():
            # 用户过滤
            if user_id and record.user_id != user_id:
                continue
            # session 过滤
            if session_id and record.session_id != session_id:
                continue

            # 简单文本匹配 + 标签匹配
            content_lower = record.content.lower()
            score = 0.0
            if query_lower in content_lower:
                score = 0.8
            elif any(query_lower in tag.lower() for tag in record.tags):
                score = 0.6
            else:
                # 词级别匹配（CJK-aware）
                query_tokens = _tokenize(query_lower)
                content_tokens = _tokenize(content_lower)
                overlap = query_tokens & content_tokens
                if query_tokens and overlap:
                    score = len(overlap) / len(query_tokens) * 0.5

            if score > 0:
                matches.append((score, record))

        # 按分数排序
        matches.sort(key=lambda x: (-x[0], -x[1].importance))
        return [record for _, record in matches[:limit]]

    async def query_by_vector(
        self,
        embedding: list[float],
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[MemoryRecord]:
        if not embedding:
            return []

        scored: list[tuple[float, MemoryRecord]] = []

        for record in self._records.values():
            if user_id and record.user_id != user_id:
                continue
            if record.embedding is None:
                continue

            # 余弦相似度
            sim = self._cosine_similarity(embedding, record.embedding)
            scored.append((sim, record))

        scored.sort(key=lambda x: -x[0])
        return [record for _, record in scored[:limit]]

    async def delete(self, record_id: str) -> bool:
        if record_id in self._records:
            del self._records[record_id]
            return True
        return False

    async def list_by_session(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        results = [
            r for r in self._records.values()
            if r.session_id == session_id
        ]
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        results = [
            r for r in self._records.values()
            if r.user_id == user_id
        ]
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
