"""
L4记忆压缩器

基于A4公理，保持L4全局知识库在合理规模（~150 facts）
"""

from datetime import datetime
from typing import Any

import numpy as np

from .types import MemoryTier, MemoryType, MemoryUnit


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
    ):
        """
        初始化L4压缩器

        Args:
            threshold: 触发压缩的facts数量阈值
            similarity_threshold: 聚类相似度阈值（0-1）
            min_cluster_size: 最小聚类大小，小于此值的cluster不压缩
        """
        self.threshold = threshold
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size

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

        # 2. 压缩每个cluster
        compressed = []
        for cluster in clusters:
            if len(cluster) >= self.min_cluster_size:
                # 压缩大cluster：保留最重要的fact
                summary_fact = self._merge_cluster(cluster)
                compressed.append(summary_fact)
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
