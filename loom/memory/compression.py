"""
L4记忆压缩器

基于A4公理，保持L4全局知识库在合理规模（~150 facts）
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from .types import MemoryTier, MemoryType, MemoryUnit

_STOP_WORDS = frozenset(
    {
        # English
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "because",
        "but",
        "and",
        "or",
        "if",
        "while",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
        "what",
        "which",
        "who",
        "whom",
        # Chinese
        "的",
        "了",
        "在",
        "是",
        "我",
        "有",
        "和",
        "就",
        "不",
        "人",
        "都",
        "一",
        "一个",
        "上",
        "也",
        "很",
        "到",
        "说",
        "要",
        "去",
        "你",
        "会",
        "着",
        "没有",
        "看",
        "好",
        "自己",
        "这",
        "他",
        "她",
        "它",
        "们",
        "那",
        "些",
        "什么",
        "没",
        "把",
        "又",
        "被",
        "从",
        "这个",
        "那个",
        "但",
        "还",
        "而",
        "对",
        "以",
        "可以",
        "这样",
        "已经",
        "因为",
        "如果",
        "所以",
        "但是",
        "就是",
        "可能",
        "这些",
        "那些",
        "或者",
        "虽然",
        "然后",
        "之后",
        "之前",
        "通过",
        "进行",
        "使用",
        "需要",
        "应该",
        "其中",
        "以及",
        "关于",
        "对于",
        "随着",
        "由于",
        "为了",
    }
)

# Pre-computed Chinese stop word list sorted by length (longest first)
# Used to split Chinese character runs into keyword segments
_CN_STOPS_SORTED: list[str] = sorted(
    (w for w in _STOP_WORDS if all("\u4e00" <= c <= "\u9fff" for c in w)),
    key=len,
    reverse=True,
)


@dataclass
class FidelityResult:
    """压缩保真度度量结果"""

    embedding_similarity: float
    keyword_retention: float
    composite_score: float
    passed: bool
    cluster_size: int
    retained_keywords: list[str] = field(default_factory=list)
    lost_keywords: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "fidelity_embedding_similarity": round(self.embedding_similarity, 4),
            "fidelity_keyword_retention": round(self.keyword_retention, 4),
            "fidelity_composite_score": round(self.composite_score, 4),
            "fidelity_passed": self.passed,
            "fidelity_lost_keywords": self.lost_keywords,
        }


class FidelityChecker:
    """
    压缩保真度检查器

    两个信号：
    1. Embedding 余弦相似度：合并 embedding 与各原始 embedding 的平均相似度
    2. 关键词保留率：原始关键词在合并内容中的出现比例
    """

    def __init__(
        self,
        threshold: float = 0.5,
        embedding_weight: float = 0.6,
        keyword_weight: float = 0.4,
        max_lost_keywords_recorded: int = 20,
    ):
        self.threshold = threshold
        self.embedding_weight = embedding_weight
        self.keyword_weight = keyword_weight
        self.max_lost_keywords_recorded = max_lost_keywords_recorded

    def check(self, merged: MemoryUnit, originals: list[MemoryUnit]) -> FidelityResult:
        embedding_sim = self._compute_embedding_similarity(merged, originals)
        keyword_ret, retained, lost = self._compute_keyword_retention(merged, originals)

        composite = self.embedding_weight * embedding_sim + self.keyword_weight * keyword_ret

        return FidelityResult(
            embedding_similarity=embedding_sim,
            keyword_retention=keyword_ret,
            composite_score=composite,
            passed=composite >= self.threshold,
            cluster_size=len(originals),
            retained_keywords=retained,
            lost_keywords=lost[: self.max_lost_keywords_recorded],
        )

    def _compute_embedding_similarity(
        self,
        merged: MemoryUnit,
        originals: list[MemoryUnit],
    ) -> float:
        if merged.embedding is None:
            return 0.0

        original_embeddings = [f.embedding for f in originals if f.embedding is not None]
        if not original_embeddings:
            return 0.0

        merged_vec = np.array(merged.embedding, dtype=np.float32)
        merged_norm = np.linalg.norm(merged_vec)
        if merged_norm == 0:
            return 0.0
        merged_normalized = merged_vec / merged_norm

        originals_array = np.array(original_embeddings, dtype=np.float32)
        norms = np.linalg.norm(originals_array, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        originals_normalized = originals_array / norms

        similarities = np.dot(originals_normalized, merged_normalized)
        similarities = np.clip(similarities, -1.0, 1.0)

        return float(np.mean(similarities))

    def _compute_keyword_retention(
        self,
        merged: MemoryUnit,
        originals: list[MemoryUnit],
    ) -> tuple[float, list[str], list[str]]:
        all_keywords: set[str] = set()
        for fact in originals:
            content = str(fact.content) if fact.content is not None else ""
            all_keywords |= self._extract_keywords(content)

        if not all_keywords:
            return 1.0, [], []

        merged_content = str(merged.content) if merged.content is not None else ""
        merged_lower = merged_content.lower()

        retained = [kw for kw in all_keywords if kw.lower() in merged_lower]
        lost = [kw for kw in all_keywords if kw.lower() not in merged_lower]

        rate = len(retained) / len(all_keywords)
        return rate, sorted(retained), sorted(lost)

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        keywords: set[str] = set()

        # Capitalized phrases: "Machine Learning"
        # Use lookarounds instead of \b to handle CJK adjacency
        for match in re.finditer(
            r"(?<![a-zA-Z])([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?![a-zA-Z])",
            text,
        ):
            keywords.add(match.group(1))

        # Standalone capitalized words (not stop words)
        for match in re.finditer(r"(?<![a-zA-Z])([A-Z][a-z]{1,})(?![a-zA-Z])", text):
            word = match.group(1)
            if word.lower() not in _STOP_WORDS:
                keywords.add(word)

        # snake_case identifiers
        for match in re.finditer(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b", text):
            keywords.add(match.group(0))

        # dotted paths: loom.memory.core
        for match in re.finditer(r"\b([a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+)\b", text):
            keywords.add(match.group(0))

        # ALL_CAPS identifiers
        for match in re.finditer(
            r"(?<![a-zA-Z])([A-Z]{2,}(?:_[A-Z0-9]+)*)(?![a-zA-Z])",
            text,
        ):
            keywords.add(match.group(1))

        # Chinese: split runs on stop words, keep meaningful segments
        for match in re.finditer(r"[\u4e00-\u9fff]+", text):
            run = match.group(0)
            # Replace stop words with separator (longest first to avoid partial matches)
            for sw in _CN_STOPS_SORTED:
                run = run.replace(sw, "\x00")
            for seg in run.split("\x00"):
                if len(seg) >= 2:
                    keywords.add(seg)

        return keywords


class L4Compressor:
    """
    L4知识库压缩器

    使用聚类和重要性评分来压缩相似的facts，保持L4在合理规模。

    压缩策略：
    1. 如果启用向量化：使用余弦相似度聚类相似facts
    2. 否则：基于重要性分数保留最重要的facts
    """

    def __init__(
        self,
        threshold: int = 150,
        similarity_threshold: float = 0.75,
        min_cluster_size: int = 3,
        fidelity_threshold: float = 0.5,
    ):
        """
        初始化L4压缩器

        Args:
            threshold: 触发压缩的facts数量阈值
            similarity_threshold: 聚类相似度阈值（0-1）
            min_cluster_size: 最小聚类大小，小于此值的cluster不压缩
            fidelity_threshold: 压缩保真度阈值，低于此值保留原始facts
        """
        self.threshold = threshold
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self._fidelity_checker = FidelityChecker(threshold=fidelity_threshold)

    async def should_compress(self, l4_facts: list[MemoryUnit]) -> bool:
        """
        判断是否需要压缩

        Args:
            l4_facts: L4层的所有facts

        Returns:
            是否需要压缩
        """
        return len(l4_facts) > self.threshold

    async def compress(self, l4_facts: list[MemoryUnit]) -> list[MemoryUnit]:
        """
        压缩L4 facts

        Args:
            l4_facts: L4层的所有facts

        Returns:
            压缩后的facts列表
        """
        if len(l4_facts) <= self.threshold:
            return l4_facts

        # 检查是否有embedding（向量化）
        has_embeddings = any(f.embedding is not None for f in l4_facts)

        if has_embeddings:
            # 使用聚类压缩
            return await self._compress_with_clustering(l4_facts)
        else:
            # 使用重要性评分压缩（降级方案）
            return self._compress_by_importance(l4_facts)

    async def _compress_with_clustering(self, facts: list[MemoryUnit]) -> list[MemoryUnit]:
        """
        使用聚类压缩facts

        Args:
            facts: 待压缩的facts列表

        Returns:
            压缩后的facts列表
        """
        # 1. 聚类相似的facts
        clusters = await self._cluster_facts(facts)

        # 2. 压缩每个cluster（带保真度检查）
        compressed = []
        for cluster in clusters:
            if len(cluster) >= self.min_cluster_size:
                merged_fact = self._merge_cluster(cluster)
                fidelity = self._fidelity_checker.check(merged_fact, cluster)
                if fidelity.passed:
                    merged_fact.metadata.update(fidelity.to_metadata())
                    compressed.append(merged_fact)
                else:
                    # 保真度不足，保留原始facts
                    compressed.extend(cluster)
            else:
                # 保留小cluster的原始facts
                compressed.extend(cluster)

        return compressed

    async def _cluster_facts(self, facts: list[MemoryUnit]) -> list[list[MemoryUnit]]:
        """
        聚类相似的facts

        使用基于相似度阈值的简单聚类算法：
        1. 计算所有facts之间的余弦相似度
        2. 使用并查集合并相似度超过阈值的facts
        3. 返回聚类结果

        Args:
            facts: 待聚类的facts列表

        Returns:
            聚类后的facts列表，每个元素是一个cluster
        """
        if len(facts) < 2:
            return [facts]

        # 获取所有embeddings
        embeddings = []
        valid_facts = []
        for fact in facts:
            if fact.embedding:
                embeddings.append(fact.embedding)
                valid_facts.append(fact)

        if len(embeddings) < 2:
            return [facts]

        # 转换为numpy数组并归一化
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # L2归一化
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # 避免除以零
        embeddings_normalized = embeddings_array / norms

        # 检查是否有无效值
        if np.any(np.isnan(embeddings_normalized)) or np.any(np.isinf(embeddings_normalized)):
            return [facts]

        # 计算余弦相似度矩阵
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)
        similarity_matrix = np.clip(similarity_matrix, -1.0, 1.0)

        # 使用并查集进行聚类
        clusters = self._union_find_clustering(
            valid_facts, similarity_matrix, self.similarity_threshold
        )

        return clusters

    def _union_find_clustering(
        self,
        facts: list[MemoryUnit],
        similarity_matrix: Any,
        threshold: float,
    ) -> list[list[MemoryUnit]]:
        """
        使用并查集进行聚类

        Args:
            facts: facts列表
            similarity_matrix: 相似度矩阵
            threshold: 相似度阈值

        Returns:
            聚类结果
        """
        n = len(facts)

        # 初始化并查集
        parent = list(range(n))
        rank = [0] * n

        def find(x: int) -> int:
            """查找根节点（带路径压缩）"""
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: int, y: int) -> None:
            """合并两个集合（按秩合并）"""
            root_x = find(x)
            root_y = find(y)

            if root_x == root_y:
                return

            if rank[root_x] < rank[root_y]:
                parent[root_x] = root_y
            elif rank[root_x] > rank[root_y]:
                parent[root_y] = root_x
            else:
                parent[root_y] = root_x
                rank[root_x] += 1

        # 遍历相似度矩阵，合并相似的facts
        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i][j] >= threshold:
                    union(i, j)

        # 组织成clusters
        clusters_dict: dict[int, list[MemoryUnit]] = {}
        for i in range(n):
            root = find(i)
            if root not in clusters_dict:
                clusters_dict[root] = []
            clusters_dict[root].append(facts[i])

        return list(clusters_dict.values())

    def _merge_cluster(self, cluster: list[MemoryUnit]) -> MemoryUnit:
        """
        合并一个cluster为单个fact

        策略：保留最重要的fact，合并metadata

        Args:
            cluster: 待合并的facts cluster

        Returns:
            合并后的单个fact
        """
        # 按重要性排序，保留最重要的
        cluster_sorted = sorted(cluster, key=lambda f: f.importance, reverse=True)
        best_fact = cluster_sorted[0]

        # 创建新的fact，保留最重要fact的内容
        merged_fact = MemoryUnit(
            content=best_fact.content,
            tier=MemoryTier.L4_GLOBAL,
            type=MemoryType.FACT,
            importance=max(f.importance for f in cluster),
            metadata={
                "compressed_from": len(cluster),
                "original_ids": [f.id for f in cluster],
                "compressed_at": datetime.now().isoformat(),
            },
            embedding=best_fact.embedding,
        )

        return merged_fact

    def _compress_by_importance(self, facts: list[MemoryUnit]) -> list[MemoryUnit]:
        """
        基于重要性评分压缩facts（降级方案）

        当没有embedding时使用此方法

        Args:
            facts: 待压缩的facts列表

        Returns:
            压缩后的facts列表
        """
        # 按重要性排序
        sorted_facts = sorted(facts, key=lambda f: f.importance, reverse=True)

        # 保留前threshold个最重要的facts
        return sorted_facts[: self.threshold]
