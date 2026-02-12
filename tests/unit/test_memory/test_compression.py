"""
L4 Compressor Unit Tests

测试L4记忆压缩器的核心功能
"""

import numpy as np
import pytest

from loom.memory.compression import FidelityChecker, FidelityResult, L4Compressor
from loom.memory.types import MemoryTier, MemoryType, MemoryUnit


class TestL4CompressorInit:
    """测试L4Compressor初始化"""

    def test_init_default(self):
        """测试默认参数初始化"""
        compressor = L4Compressor()

        assert compressor.threshold == 150
        assert compressor.similarity_threshold == 0.75
        assert compressor.min_cluster_size == 3
        assert compressor._fidelity_checker.threshold == 0.5

    def test_init_custom_parameters(self):
        """测试自定义参数初始化"""
        compressor = L4Compressor(
            threshold=200,
            similarity_threshold=0.8,
            min_cluster_size=5,
            fidelity_threshold=0.7,
        )

        assert compressor.threshold == 200
        assert compressor.similarity_threshold == 0.8
        assert compressor.min_cluster_size == 5
        assert compressor._fidelity_checker.threshold == 0.7


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


# ── Fidelity Tests ──


class TestFidelityResult:
    def test_to_metadata_contains_all_fields(self):
        result = FidelityResult(
            embedding_similarity=0.85,
            keyword_retention=0.7,
            composite_score=0.79,
            passed=True,
            cluster_size=4,
            retained_keywords=["Python", "API"],
            lost_keywords=["Redis"],
        )
        meta = result.to_metadata()
        assert meta["fidelity_embedding_similarity"] == 0.85
        assert meta["fidelity_keyword_retention"] == 0.7
        assert meta["fidelity_composite_score"] == 0.79
        assert meta["fidelity_passed"] is True
        assert meta["fidelity_lost_keywords"] == ["Redis"]

    def test_to_metadata_rounds_floats(self):
        result = FidelityResult(
            embedding_similarity=0.123456789,
            keyword_retention=0.987654321,
            composite_score=0.555555555,
            passed=True,
            cluster_size=3,
            retained_keywords=[],
            lost_keywords=[],
        )
        meta = result.to_metadata()
        assert meta["fidelity_embedding_similarity"] == 0.1235
        assert meta["fidelity_keyword_retention"] == 0.9877


class TestFidelityCheckerKeywordExtraction:
    def test_extracts_capitalized_words(self):
        keywords = FidelityChecker._extract_keywords("Python is great for Machine Learning")
        assert "Python" in keywords
        assert "Machine Learning" in keywords

    def test_ignores_stop_words(self):
        keywords = FidelityChecker._extract_keywords("The quick Brown fox")
        assert "Brown" in keywords
        assert "The" not in keywords

    def test_extracts_snake_case(self):
        keywords = FidelityChecker._extract_keywords("use memory_manager to store data")
        assert "memory_manager" in keywords

    def test_extracts_dotted_paths(self):
        keywords = FidelityChecker._extract_keywords("import loom.memory.core module")
        assert "loom.memory.core" in keywords

    def test_extracts_all_caps(self):
        keywords = FidelityChecker._extract_keywords("Set the API_KEY and HTTP_TIMEOUT")
        assert "API_KEY" in keywords
        assert "HTTP_TIMEOUT" in keywords

    def test_empty_string(self):
        keywords = FidelityChecker._extract_keywords("")
        assert keywords == set()

    def test_no_keywords_in_plain_lowercase(self):
        keywords = FidelityChecker._extract_keywords("this is all lowercase text")
        assert len(keywords) == 0

    def test_extracts_chinese_keywords(self):
        keywords = FidelityChecker._extract_keywords("向量检索的召回率随着记忆量增长而下降")
        assert "向量检索" in keywords
        assert "召回率" in keywords
        assert "记忆量增长" in keywords

    def test_chinese_stop_words_filtered(self):
        keywords = FidelityChecker._extract_keywords("可以使用已经通过的方案")
        # "可以", "使用", "已经", "通过" are stop words
        # Only non-stop sequences should remain
        for kw in keywords:
            assert kw not in {"可以", "使用", "已经", "通过"}

    def test_mixed_chinese_english(self):
        keywords = FidelityChecker._extract_keywords("使用Python进行向量检索和Redis缓存")
        assert "Python" in keywords
        assert "Redis" in keywords
        assert "向量检索" in keywords


class TestFidelityCheckerEmbeddingSimilarity:
    def test_identical_embeddings_score_1(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="a", embedding=[1.0, 0.0, 0.0])
        originals = [
            MemoryUnit(content="a", embedding=[1.0, 0.0, 0.0]),
            MemoryUnit(content="b", embedding=[1.0, 0.0, 0.0]),
        ]
        score = checker._compute_embedding_similarity(merged, originals)
        assert abs(score - 1.0) < 1e-6

    def test_orthogonal_embeddings_score_0(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="a", embedding=[1.0, 0.0, 0.0])
        originals = [
            MemoryUnit(content="b", embedding=[0.0, 1.0, 0.0]),
            MemoryUnit(content="c", embedding=[0.0, 0.0, 1.0]),
        ]
        score = checker._compute_embedding_similarity(merged, originals)
        assert abs(score) < 1e-6

    def test_mixed_similarity(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="a", embedding=[1.0, 0.0, 0.0])
        originals = [
            MemoryUnit(content="a", embedding=[1.0, 0.0, 0.0]),  # sim = 1.0
            MemoryUnit(content="b", embedding=[0.0, 1.0, 0.0]),  # sim = 0.0
        ]
        score = checker._compute_embedding_similarity(merged, originals)
        assert abs(score - 0.5) < 1e-6

    def test_no_merged_embedding_returns_0(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="a", embedding=None)
        originals = [MemoryUnit(content="b", embedding=[1.0, 0.0])]
        assert checker._compute_embedding_similarity(merged, originals) == 0.0

    def test_no_original_embeddings_returns_0(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="a", embedding=[1.0, 0.0])
        originals = [MemoryUnit(content="b", embedding=None)]
        assert checker._compute_embedding_similarity(merged, originals) == 0.0


class TestFidelityCheckerKeywordRetention:
    def test_full_retention(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="Python API for Machine Learning")
        originals = [
            MemoryUnit(content="Python is useful"),
            MemoryUnit(content="Machine Learning API"),
        ]
        rate, retained, lost = checker._compute_keyword_retention(merged, originals)
        assert rate == 1.0
        assert len(lost) == 0

    def test_partial_retention(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="Python is useful")
        originals = [
            MemoryUnit(content="Python is useful"),
            MemoryUnit(content="Redis cache configuration"),
        ]
        rate, retained, lost = checker._compute_keyword_retention(merged, originals)
        assert "Python" in retained
        assert "Redis" in lost
        assert 0.0 < rate < 1.0

    def test_no_keywords_returns_1(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="all lowercase")
        originals = [MemoryUnit(content="also lowercase")]
        rate, retained, lost = checker._compute_keyword_retention(merged, originals)
        assert rate == 1.0

    def test_none_content_handled(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content=None)
        originals = [MemoryUnit(content=None)]
        rate, _, _ = checker._compute_keyword_retention(merged, originals)
        assert rate == 1.0


class TestFidelityCheckerCheck:
    def test_high_fidelity_passes(self):
        checker = FidelityChecker(threshold=0.5)
        merged = MemoryUnit(
            content="Python API for Machine Learning",
            embedding=[1.0, 0.0, 0.0],
        )
        originals = [
            MemoryUnit(content="Python API reference", embedding=[0.95, 0.05, 0.0]),
            MemoryUnit(content="Machine Learning with Python", embedding=[0.9, 0.1, 0.0]),
            MemoryUnit(content="Python API docs", embedding=[0.98, 0.02, 0.0]),
        ]
        result = checker.check(merged, originals)
        assert result.passed is True
        assert result.composite_score >= 0.5

    def test_low_fidelity_fails(self):
        checker = FidelityChecker(threshold=0.8)
        merged = MemoryUnit(
            content="simple text",
            embedding=[1.0, 0.0, 0.0],
        )
        originals = [
            MemoryUnit(content="Redis Configuration Guide", embedding=[0.0, 1.0, 0.0]),
            MemoryUnit(content="PostgreSQL Indexing Strategy", embedding=[0.0, 0.0, 1.0]),
            MemoryUnit(content="MongoDB Sharding Setup", embedding=[0.0, 0.5, 0.5]),
        ]
        result = checker.check(merged, originals)
        assert result.passed is False
        assert result.composite_score < 0.8

    def test_result_cluster_size(self):
        checker = FidelityChecker()
        merged = MemoryUnit(content="test", embedding=[1.0])
        originals = [MemoryUnit(content="a", embedding=[1.0]) for _ in range(5)]
        result = checker.check(merged, originals)
        assert result.cluster_size == 5

    def test_lost_keywords_capped(self):
        checker = FidelityChecker(max_lost_keywords_recorded=3)
        originals = [MemoryUnit(content=f"Keyword{i} is important") for i in range(10)]
        merged = MemoryUnit(content="nothing relevant here")
        result = checker.check(merged, originals)
        assert len(result.lost_keywords) <= 3


class TestCompressWithFidelity:
    @pytest.mark.asyncio
    async def test_high_fidelity_merge_proceeds(self):
        """高保真时正常合并，metadata 包含 fidelity 信息"""
        compressor = L4Compressor(
            threshold=3,
            min_cluster_size=3,
            fidelity_threshold=0.3,
        )
        facts = [
            MemoryUnit(
                content="Python API reference guide",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=float(i),
                embedding=[1.0, 0.0, 0.0],
            )
            for i in range(4)
        ]
        result = await compressor.compress(facts)
        assert len(result) < 4
        merged = [f for f in result if "fidelity_composite_score" in f.metadata]
        assert len(merged) == 1
        assert merged[0].metadata["fidelity_passed"] is True

    @pytest.mark.asyncio
    async def test_low_fidelity_keeps_originals(self):
        """保真度不足时保留原始 facts"""
        compressor = L4Compressor(
            threshold=3,
            min_cluster_size=3,
            similarity_threshold=0.3,
            fidelity_threshold=0.99,
        )
        # Each fact has distinct keywords but similar embeddings (will cluster)
        contents = [
            "Redis Configuration Guide",
            "PostgreSQL Indexing Strategy",
            "MongoDB Sharding Setup",
            "Elasticsearch Query Optimization",
        ]
        facts = [
            MemoryUnit(
                content=contents[i],
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=0.5,
                embedding=[0.8, 0.1 + i * 0.02, 0.1],
            )
            for i in range(4)
        ]
        result = await compressor.compress(facts)
        assert len(result) == 4
