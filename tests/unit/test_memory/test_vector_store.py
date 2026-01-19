"""
Vector Store Unit Tests

测试向量存储功能
"""

import pytest

from loom.memory.vector_store import (
    EmbeddingProvider,
    InMemoryVectorStore,
    VectorSearchResult,
    VectorStoreProvider,
)


class TestInMemoryVectorStore:
    """测试 InMemoryVectorStore"""

    @pytest.fixture
    def vector_store(self):
        """提供向量存储实例"""
        return InMemoryVectorStore()

    @pytest.mark.asyncio
    async def test_add(self, vector_store):
        """测试添加向量"""
        embedding = [0.1, 0.2, 0.3, 0.4]
        metadata = {"key": "value"}

        result = await vector_store.add("vec-1", embedding, metadata)

        assert result is True
        assert "vec-1" in vector_store._vectors
        assert vector_store._metadata["vec-1"] == metadata

    @pytest.mark.asyncio
    async def test_add_without_metadata(self, vector_store):
        """测试添加向量（无元数据）"""
        embedding = [0.1, 0.2, 0.3]

        result = await vector_store.add("vec-1", embedding)

        assert result is True
        assert vector_store._metadata["vec-1"] == {}

    @pytest.mark.asyncio
    async def test_search_empty(self, vector_store):
        """测试搜索空存储"""
        query_embedding = [0.1, 0.2, 0.3]

        results = await vector_store.search(query_embedding, top_k=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_similar(self, vector_store):
        """测试搜索相似向量"""
        # 添加一些向量
        await vector_store.add("vec-1", [1.0, 0.0, 0.0], {"name": "vector1"})
        await vector_store.add("vec-2", [0.0, 1.0, 0.0], {"name": "vector2"})
        await vector_store.add("vec-3", [0.0, 0.0, 1.0], {"name": "vector3"})

        # 搜索与 vec-1 相似的向量
        query = [1.0, 0.0, 0.0]
        results = await vector_store.search(query, top_k=2)

        assert len(results) == 2
        assert results[0].id == "vec-1"
        assert results[0].score == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_search_with_top_k(self, vector_store):
        """测试带 top_k 的搜索"""
        # 添加多个向量
        for i in range(10):
            embedding = [float(i), 0.0, 0.0]
            await vector_store.add(f"vec-{i}", embedding)

        query = [5.0, 0.0, 0.0]
        results = await vector_store.search(query, top_k=3)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_zero_query(self, vector_store):
        """测试零向量查询"""
        await vector_store.add("vec-1", [1.0, 0.0, 0.0])

        query = [0.0, 0.0, 0.0]
        results = await vector_store.search(query, top_k=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_zero_vector(self, vector_store):
        """测试存储中的零向量"""
        await vector_store.add("vec-1", [0.0, 0.0, 0.0])
        await vector_store.add("vec-2", [1.0, 0.0, 0.0])

        query = [1.0, 0.0, 0.0]
        results = await vector_store.search(query, top_k=5)

        # 应该只返回非零向量
        assert len(results) == 1
        assert results[0].id == "vec-2"

    @pytest.mark.asyncio
    async def test_clear(self, vector_store):
        """测试清空存储"""
        await vector_store.add("vec-1", [1.0, 0.0, 0.0])
        await vector_store.add("vec-2", [0.0, 1.0, 0.0])

        result = await vector_store.clear()

        assert result is True
        assert len(vector_store._vectors) == 0
        assert len(vector_store._metadata) == 0

    @pytest.mark.asyncio
    async def test_search_results_format(self, vector_store):
        """测试搜索结果格式"""
        await vector_store.add("vec-1", [1.0, 0.0, 0.0], {"key": "value"})

        query = [1.0, 0.0, 0.0]
        results = await vector_store.search(query, top_k=1)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, VectorSearchResult)
        assert result.id == "vec-1"
        assert isinstance(result.score, float)
        assert result.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_search_cosine_similarity(self, vector_store):
        """测试余弦相似度计算"""
        # 添加两个正交向量
        await vector_store.add("vec-1", [1.0, 0.0], {"name": "x-axis"})
        await vector_store.add("vec-2", [0.0, 1.0], {"name": "y-axis"})

        # 查询 x 轴方向
        query = [1.0, 0.0]
        results = await vector_store.search(query, top_k=2)

        assert len(results) == 2
        # vec-1 应该完全匹配（相似度=1）
        assert results[0].id == "vec-1"
        assert results[0].score == pytest.approx(1.0, abs=0.01)
        # vec-2 应该正交（相似度=0）
        assert results[1].id == "vec-2"
        assert results[1].score == pytest.approx(0.0, abs=0.01)


class TestVectorSearchResult:
    """测试 VectorSearchResult"""

    def test_vector_search_result_init(self):
        """测试 VectorSearchResult 初始化"""
        result = VectorSearchResult(
            id="test-id",
            score=0.95,
            metadata={"key": "value"},
        )

        assert result.id == "test-id"
        assert result.score == 0.95
        assert result.metadata == {"key": "value"}


class TestEmbeddingProvider:
    """测试 EmbeddingProvider 抽象类"""

    def test_embedding_provider_is_abstract(self):
        """测试 EmbeddingProvider 是抽象类"""
        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore


class TestVectorStoreProvider:
    """测试 VectorStoreProvider 抽象类"""

    def test_vector_store_provider_is_abstract(self):
        """测试 VectorStoreProvider 是抽象类"""
        with pytest.raises(TypeError):
            VectorStoreProvider()  # type: ignore
