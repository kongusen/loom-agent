"""
Tests for Memory Vector Store
"""

import numpy as np
import pytest

from loom.memory.vector_store import InMemoryVectorStore, VectorSearchResult, VectorStoreProvider


class TestVectorSearchResult:
    """Test VectorSearchResult dataclass."""

    def test_create_result(self):
        """Test creating a search result."""
        result = VectorSearchResult(id="test_id", score=0.95, metadata={"key": "value"})

        assert result.id == "test_id"
        assert result.score == 0.95
        assert result.metadata == {"key": "value"}

    def test_create_with_empty_metadata(self):
        """Test creating result with empty metadata."""
        result = VectorSearchResult(id="test_id", score=0.5, metadata={})

        assert result.metadata == {}


class TestVectorStoreProvider:
    """Test abstract VectorStoreProvider class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that VectorStoreProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            VectorStoreProvider()


@pytest.mark.asyncio
class TestInMemoryVectorStore:
    """Test InMemoryVectorStore implementation."""

    @pytest.fixture
    def store(self):
        """Create a fresh store for each test."""
        return InMemoryVectorStore()

    @pytest.fixture
    def sample_embedding(self):
        """Create a sample embedding."""
        return [0.1, 0.2, 0.3, 0.4, 0.5]

    async def test_initialization(self, store):
        """Test store initialization."""
        assert store._vectors == {}
        assert store._texts == {}
        assert store._metadata == {}

    async def test_add_vector(self, store, sample_embedding):
        """Test adding a vector."""
        result = await store.add(
            id="doc1",
            text="test document",
            embedding=sample_embedding,
            metadata={"category": "test"},
        )

        assert result is True
        assert "doc1" in store._vectors
        assert "doc1" in store._texts
        assert "doc1" in store._metadata

    async def test_add_multiple_vectors(self, store, sample_embedding):
        """Test adding multiple vectors."""
        await store.add("doc1", "text1", sample_embedding, {"tag": "a"})
        await store.add("doc2", "text2", sample_embedding, {"tag": "b"})
        await store.add("doc3", "text3", sample_embedding, {"tag": "c"})

        assert len(store._vectors) == 3
        assert len(store._texts) == 3
        assert len(store._metadata) == 3

    async def test_add_with_none_metadata(self, store, sample_embedding):
        """Test adding vector with None metadata."""
        result = await store.add(id="doc1", text="test", embedding=sample_embedding, metadata=None)

        assert result is True
        assert store._metadata["doc1"] == {}

    async def test_search_empty_store(self, store, sample_embedding):
        """Test searching empty store returns empty list."""
        results = await store.search(sample_embedding)

        assert results == []

    async def test_search_returns_results(self, store, sample_embedding):
        """Test that search returns results."""
        await store.add("doc1", "similar text", sample_embedding, {"tag": "a"})

        results = await store.search(sample_embedding)

        assert len(results) == 1
        assert results[0].id == "doc1"
        assert results[0].score > 0  # Should have high similarity with itself
        assert results[0].metadata == {"tag": "a"}

    async def test_search_with_top_k(self, store, sample_embedding):
        """Test search with top_k parameter."""
        # Add multiple vectors
        for i in range(5):
            embedding = [0.1 * (i + 1)] * 5
            await store.add(f"doc{i}", f"text{i}", embedding)

        results = await store.search(sample_embedding, top_k=3)

        assert len(results) == 3

    async def test_search_with_metadata_filter(self, store, sample_embedding):
        """Test search with metadata filtering."""
        await store.add("doc1", "text1", sample_embedding, {"category": "tech"})
        await store.add("doc2", "text2", sample_embedding, {"category": "news"})

        # Filter for tech category
        results = await store.search(sample_embedding, filter_metadata={"category": "tech"})

        assert len(results) == 1
        assert results[0].id == "doc1"

    async def test_search_filters_non_matching(self, store, sample_embedding):
        """Test that non-matching metadata is filtered out."""
        await store.add("doc1", "text1", sample_embedding, {"tag": "a"})
        await store.add("doc2", "text2", sample_embedding, {"tag": "b"})

        results = await store.search(sample_embedding, filter_metadata={"tag": "c"})

        assert len(results) == 0

    async def test_search_scores_ordering(self, store):
        """Test that results are ordered by score (descending)."""
        # Create embeddings with different similarities
        query = [1.0, 0.0, 0.0, 0.0, 0.0]

        await store.add("doc1", "text1", [1.0, 0.0, 0.0, 0.0, 0.0])  # Exact match
        await store.add("doc2", "text2", [0.9, 0.1, 0.0, 0.0, 0.0])  # Similar
        await store.add("doc3", "text3", [0.0, 1.0, 0.0, 0.0, 0.0])  # Different

        results = await store.search(query, top_k=3)

        # Results should be in descending score order
        assert results[0].score >= results[1].score >= results[2].score

    async def test_delete_existing_vector(self, store, sample_embedding):
        """Test deleting an existing vector."""
        await store.add("doc1", "text1", sample_embedding)

        result = await store.delete("doc1")

        assert result is True
        assert "doc1" not in store._vectors

    async def test_delete_nonexistent_vector(self, store):
        """Test deleting a nonexistent vector."""
        result = await store.delete("nonexistent")

        assert result is False

    async def test_update_embedding(self, store, sample_embedding):
        """Test updating vector embedding."""
        await store.add("doc1", "text1", sample_embedding)

        new_embedding = [0.5, 0.5, 0.5, 0.5, 0.5]
        result = await store.update("doc1", embedding=new_embedding)

        assert result is True
        np.testing.assert_array_almost_equal(store._vectors["doc1"], np.array(new_embedding))

    async def test_update_metadata(self, store, sample_embedding):
        """Test updating vector metadata."""
        await store.add("doc1", "text1", sample_embedding, {"tag": "old"})

        result = await store.update("doc1", metadata={"tag": "new"})

        assert result is True
        assert store._metadata["doc1"]["tag"] == "new"

    async def test_update_nonexistent_vector(self, store):
        """Test updating a nonexistent vector."""
        result = await store.update("nonexistent", embedding=[0.1, 0.2])

        assert result is False

    async def test_update_both_embedding_and_metadata(self, store, sample_embedding):
        """Test updating both embedding and metadata."""
        await store.add("doc1", "text1", sample_embedding, {"v": 1})

        new_embedding = [0.9, 0.8, 0.7, 0.6, 0.5]
        result = await store.update("doc1", embedding=new_embedding, metadata={"v": 2})

        assert result is True
        np.testing.assert_array_almost_equal(store._vectors["doc1"], np.array(new_embedding))
        assert store._metadata["doc1"]["v"] == 2

    async def test_get_existing_vector(self, store, sample_embedding):
        """Test retrieving an existing vector."""
        await store.add("doc1", "text1", sample_embedding, {"key": "value"})

        result = await store.get("doc1")

        assert result is not None
        assert result.id == "doc1"
        assert result.score == 1.0
        assert result.metadata == {"key": "value"}

    async def test_get_nonexistent_vector(self, store):
        """Test retrieving a nonexistent vector."""
        result = await store.get("nonexistent")

        assert result is None

    async def test_clear_store(self, store, sample_embedding):
        """Test clearing all vectors."""
        await store.add("doc1", "text1", sample_embedding)
        await store.add("doc2", "text2", sample_embedding)

        result = await store.clear()

        assert result is True
        assert len(store._vectors) == 0
        assert len(store._texts) == 0
        assert len(store._metadata) == 0

    def test_matches_filter_exact_match(self, store):
        """Test _matches_filter with exact match."""
        metadata = {"category": "tech", "tag": "important"}
        filter_dict = {"category": "tech"}

        result = store._matches_filter(metadata, filter_dict)

        assert result is True

    def test_matches_filter_no_match(self, store):
        """Test _matches_filter with no match."""
        metadata = {"category": "tech"}
        filter_dict = {"category": "news"}

        result = store._matches_filter(metadata, filter_dict)

        assert result is False

    def test_matches_filter_missing_key(self, store):
        """Test _matches_filter when metadata is missing filter key."""
        metadata = {"category": "tech"}
        filter_dict = {"category": "tech", "tag": "important"}

        result = store._matches_filter(metadata, filter_dict)

        assert result is False

    def test_matches_filter_empty_filter(self, store):
        """Test _matches_filter with empty filter."""
        metadata = {"category": "tech"}
        filter_dict = {}

        result = store._matches_filter(metadata, filter_dict)

        assert result is True

    def test_matches_filter_multiple_criteria(self, store):
        """Test _matches_filter with multiple filter criteria."""
        metadata = {"category": "tech", "tag": "important", "author": "john"}
        filter_dict = {"category": "tech", "tag": "important"}

        result = store._matches_filter(metadata, filter_dict)

        assert result is True

    async def test_add_overwrites_existing(self, store, sample_embedding):
        """Test that adding same ID overwrites existing."""
        await store.add("doc1", "text1", sample_embedding, {"v": 1})

        new_embedding = [0.9, 0.9, 0.9, 0.9, 0.9]
        await store.add("doc1", "text2", new_embedding, {"v": 2})

        # Should have new values
        assert store._texts["doc1"] == "text2"
        assert store._metadata["doc1"]["v"] == 2

    async def test_search_with_different_dimensions(self, store):
        """Test search with embedding of different dimension raises error."""
        await store.add("doc1", "text1", [0.1, 0.2, 0.3])

        # Search with different dimension should raise error
        with pytest.raises(ValueError):
            await store.search([0.1, 0.2])

    async def test_cosine_similarity_calculation(self, store):
        """Test that cosine similarity is calculated correctly."""
        # Orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        await store.add("doc1", "text1", vec1)

        results = await store.search(vec2)

        # Orthogonal vectors should have similarity near 0
        assert abs(results[0].score) < 0.01

    async def test_identical_vectors_max_similarity(self, store, sample_embedding):
        """Test that identical vectors have maximum similarity."""
        await store.add("doc1", "text1", sample_embedding)

        results = await store.search(sample_embedding)

        # Identical vectors should have similarity close to 1
        assert results[0].score > 0.99
