"""
L4 Compressor Unit Tests

测试L4记忆压缩器的核心功能
"""

import numpy as np
import pytest

from loom.memory.compression import L4Compressor
from loom.memory.types import MemoryTier, MemoryType, MemoryUnit


class TestL4CompressorInit:
    """测试L4Compressor初始化"""

    def test_init_default(self):
        """测试默认参数初始化"""
        compressor = L4Compressor()

        assert compressor.threshold == 150
        assert compressor.similarity_threshold == 0.75
        assert compressor.min_cluster_size == 3

    def test_init_custom_parameters(self):
        """测试自定义参数初始化"""
        compressor = L4Compressor(threshold=200, similarity_threshold=0.8, min_cluster_size=5)

        assert compressor.threshold == 200
        assert compressor.similarity_threshold == 0.8
        assert compressor.min_cluster_size == 5


class TestShouldCompress:
    """测试should_compress方法"""

    @pytest.mark.asyncio
    async def test_should_compress_below_threshold(self):
        """测试低于阈值时不压缩"""
        compressor = L4Compressor(threshold=150)
        facts = [
            MemoryUnit(content=f"fact_{i}", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)
            for i in range(100)
        ]

        result = await compressor.should_compress(facts)

        assert result is False

    @pytest.mark.asyncio
    async def test_should_compress_above_threshold(self):
        """测试超过阈值时需要压缩"""
        compressor = L4Compressor(threshold=150)
        facts = [
            MemoryUnit(content=f"fact_{i}", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)
            for i in range(200)
        ]

        result = await compressor.should_compress(facts)

        assert result is True

    @pytest.mark.asyncio
    async def test_should_compress_at_threshold(self):
        """测试等于阈值时不压缩"""
        compressor = L4Compressor(threshold=150)
        facts = [
            MemoryUnit(content=f"fact_{i}", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)
            for i in range(150)
        ]

        result = await compressor.should_compress(facts)

        assert result is False


class TestCompressByImportance:
    """测试基于重要性的压缩方法"""

    def test_compress_by_importance_keeps_top_facts(self):
        """测试保留最重要的facts"""
        compressor = L4Compressor(threshold=5)
        facts = [
            MemoryUnit(
                content=f"fact_{i}",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=float(i),
            )
            for i in range(10)
        ]

        result = compressor._compress_by_importance(facts)

        assert len(result) == 5
        # 应该保留importance最高的5个（9, 8, 7, 6, 5）
        importances = [f.importance for f in result]
        assert importances == [9.0, 8.0, 7.0, 6.0, 5.0]

    def test_compress_by_importance_preserves_order(self):
        """测试按重要性排序"""
        compressor = L4Compressor(threshold=3)
        facts = [
            MemoryUnit(
                content="low", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT, importance=1.0
            ),
            MemoryUnit(
                content="high", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT, importance=10.0
            ),
            MemoryUnit(
                content="medium", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT, importance=5.0
            ),
        ]

        result = compressor._compress_by_importance(facts)

        assert len(result) == 3
        assert result[0].content == "high"
        assert result[1].content == "medium"
        assert result[2].content == "low"


class TestMergeCluster:
    """测试cluster合并方法"""

    def test_merge_cluster_keeps_most_important(self):
        """测试保留最重要的fact"""
        compressor = L4Compressor()
        cluster = [
            MemoryUnit(
                content="low importance",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=1.0,
            ),
            MemoryUnit(
                content="high importance",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=10.0,
            ),
            MemoryUnit(
                content="medium importance",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=5.0,
            ),
        ]

        result = compressor._merge_cluster(cluster)

        assert result.content == "high importance"
        assert result.importance == 10.0

    def test_merge_cluster_metadata(self):
        """测试合并后的metadata"""
        compressor = L4Compressor()
        cluster = [
            MemoryUnit(
                id="fact_1",
                content="fact 1",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=5.0,
            ),
            MemoryUnit(
                id="fact_2",
                content="fact 2",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=3.0,
            ),
        ]

        result = compressor._merge_cluster(cluster)

        assert result.metadata["compressed_from"] == 2
        assert "fact_1" in result.metadata["original_ids"]
        assert "fact_2" in result.metadata["original_ids"]
        assert "compressed_at" in result.metadata


class TestCompress:
    """测试主compress方法"""

    @pytest.mark.asyncio
    async def test_compress_below_threshold_no_change(self):
        """测试低于阈值时不压缩"""
        compressor = L4Compressor(threshold=10)
        facts = [
            MemoryUnit(
                content=f"fact_{i}",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=float(i),
            )
            for i in range(5)
        ]

        result = await compressor.compress(facts)

        assert len(result) == 5
        assert result == facts

    @pytest.mark.asyncio
    async def test_compress_without_embeddings_uses_importance(self):
        """测试无embedding时使用重要性压缩"""
        compressor = L4Compressor(threshold=5)
        facts = [
            MemoryUnit(
                content=f"fact_{i}",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=float(i),
            )
            for i in range(10)
        ]

        result = await compressor.compress(facts)

        # 应该使用重要性压缩，保留前5个最重要的
        assert len(result) == 5
        importances = [f.importance for f in result]
        assert importances == [9.0, 8.0, 7.0, 6.0, 5.0]


class TestUnionFindClustering:
    """测试并查集聚类算法"""

    def test_union_find_no_similar_facts(self):
        """测试无相似facts时每个fact独立成cluster"""
        compressor = L4Compressor()
        facts = [
            MemoryUnit(content=f"fact_{i}", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)
            for i in range(3)
        ]
        # 相似度矩阵：所有facts不相似
        similarity_matrix = np.array([[1.0, 0.1, 0.2], [0.1, 1.0, 0.15], [0.2, 0.15, 1.0]])

        result = compressor._union_find_clustering(facts, similarity_matrix, 0.75)

        # 应该有3个独立的cluster
        assert len(result) == 3

    def test_union_find_all_similar_facts(self):
        """测试所有facts相似时合并为一个cluster"""
        compressor = L4Compressor()
        facts = [
            MemoryUnit(content=f"fact_{i}", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)
            for i in range(3)
        ]
        # 相似度矩阵：所有facts都相似
        similarity_matrix = np.array([[1.0, 0.9, 0.85], [0.9, 1.0, 0.88], [0.85, 0.88, 1.0]])

        result = compressor._union_find_clustering(facts, similarity_matrix, 0.75)

        # 应该合并为1个cluster
        assert len(result) == 1
        assert len(result[0]) == 3


class TestClusterFacts:
    """测试facts聚类方法"""

    @pytest.mark.asyncio
    async def test_cluster_facts_no_embeddings(self):
        """测试无embedding时返回原始列表"""
        compressor = L4Compressor()
        facts = [
            MemoryUnit(content=f"fact_{i}", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)
            for i in range(3)
        ]

        result = await compressor._cluster_facts(facts)

        # 无embedding时应该返回原始列表
        assert len(result) == 1
        assert result[0] == facts

    @pytest.mark.asyncio
    async def test_cluster_facts_with_embeddings(self):
        """测试有embedding时进行聚类"""
        compressor = L4Compressor(similarity_threshold=0.8)
        # 创建3个facts，其中2个相似
        facts = [
            MemoryUnit(
                content="fact_0",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                embedding=[1.0, 0.0, 0.0],
            ),
            MemoryUnit(
                content="fact_1",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                embedding=[0.9, 0.1, 0.0],  # 与fact_0相似
            ),
            MemoryUnit(
                content="fact_2",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                embedding=[0.0, 0.0, 1.0],  # 与其他不相似
            ),
        ]

        result = await compressor._cluster_facts(facts)

        # 应该有2个cluster：[fact_0, fact_1] 和 [fact_2]
        assert len(result) == 2
