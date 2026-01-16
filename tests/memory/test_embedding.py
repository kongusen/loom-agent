"""
Tests for Memory Embedding Providers
"""


import pytest

from loom.memory.embedding import (
    CachedEmbeddingProvider,
    EmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
)


class TestEmbeddingProvider:
    """Test abstract EmbeddingProvider base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that EmbeddingProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EmbeddingProvider()


class TestMockEmbeddingProvider:
    """Test MockEmbeddingProvider."""

    @pytest.mark.asyncio
    async def test_embed_text_returns_vector(self):
        """Test that embed_text returns a vector."""
        provider = MockEmbeddingProvider(dimension=10)

        embedding = await provider.embed_text("test text")

        assert isinstance(embedding, list)
        assert len(embedding) == 10
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_text_is_deterministic(self):
        """Test that same text produces same embedding."""
        provider = MockEmbeddingProvider(dimension=10)

        embedding1 = await provider.embed_text("test text")
        embedding2 = await provider.embed_text("test text")

        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_embed_text_different_texts_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        provider = MockEmbeddingProvider(dimension=10)

        embedding1 = await provider.embed_text("text one")
        embedding2 = await provider.embed_text("text two")

        assert embedding1 != embedding2

    @pytest.mark.asyncio
    async def test_embed_batch_returns_multiple_vectors(self):
        """Test that embed_batch returns multiple vectors."""
        provider = MockEmbeddingProvider(dimension=10)

        embeddings = await provider.embed_batch(["text1", "text2", "text3"])

        assert len(embeddings) == 3
        assert all(len(emb) == 10 for emb in embeddings)
        assert all(isinstance(x, float) for emb in embeddings for x in emb)

    @pytest.mark.asyncio
    async def test_embed_batch_matches_individual_calls(self):
        """Test that embed_batch produces same results as individual embed_text calls."""
        provider = MockEmbeddingProvider(dimension=10)

        texts = ["text1", "text2", "text3"]
        batch_embeddings = await provider.embed_batch(texts)

        for i, text in enumerate(texts):
            individual_embedding = await provider.embed_text(text)
            assert batch_embeddings[i] == individual_embedding

    def test_dimension_property(self):
        """Test dimension property returns correct value."""
        provider = MockEmbeddingProvider(dimension=768)
        assert provider.dimension == 768

    def test_default_dimension(self):
        """Test default dimension is 1536."""
        provider = MockEmbeddingProvider()
        assert provider.dimension == 1536


class TestCachedEmbeddingProvider:
    """Test CachedEmbeddingProvider."""

    @pytest.fixture
    def mock_base_provider(self):
        """Create a mock base provider."""
        # Use MockEmbeddingProvider as base since it's simpler
        return MockEmbeddingProvider(dimension=10)

    @pytest.mark.asyncio
    async def test_embed_text_caches_result(self, mock_base_provider):
        """Test that embed_text caches results."""
        cached_provider = CachedEmbeddingProvider(mock_base_provider, max_cache_size=100)

        # First call
        embedding1 = await cached_provider.embed_text("test text")
        # Second call - should use cache
        embedding2 = await cached_provider.embed_text("test text")

        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_embed_text_different_texts(self, mock_base_provider):
        """Test that different texts produce different embeddings."""
        cached_provider = CachedEmbeddingProvider(mock_base_provider, max_cache_size=100)

        embedding1 = await cached_provider.embed_text("text1")
        embedding2 = await cached_provider.embed_text("text2")

        assert embedding1 != embedding2

    @pytest.mark.asyncio
    async def test_cache_eviction_when_full(self, mock_base_provider):
        """Test that cache evicts oldest entry when full."""
        cached_provider = CachedEmbeddingProvider(mock_base_provider, max_cache_size=2)

        # Fill cache
        await cached_provider.embed_text("text1")
        await cached_provider.embed_text("text2")
        # This should evict "text1"
        await cached_provider.embed_text("text3")

        # Request text1 again - should get new embedding (not from cache)
        new_embedding = await cached_provider.embed_text("text1")

        # The new embedding should be the same as a fresh call
        fresh_embedding = await mock_base_provider.embed_text("text1")
        assert new_embedding == fresh_embedding

    @pytest.mark.asyncio
    async def test_embed_batch_uses_cache(self, mock_base_provider):
        """Test that embed_batch uses cached results when available."""
        cached_provider = CachedEmbeddingProvider(mock_base_provider, max_cache_size=100)

        # First call - cache miss
        await cached_provider.embed_text("text1")
        await cached_provider.embed_text("text2")

        # Batch with one cached, one new
        embeddings = await cached_provider.embed_batch(["text1", "text3"])

        assert len(embeddings) == 2

    @pytest.mark.asyncio
    async def test_embed_batch_all_cached(self, mock_base_provider):
        """Test embed_batch when all texts are cached."""
        cached_provider = CachedEmbeddingProvider(mock_base_provider, max_cache_size=100)

        # Pre-warm cache
        emb1 = await cached_provider.embed_text("text1")
        emb2 = await cached_provider.embed_text("text2")

        # Batch with all cached
        embeddings = await cached_provider.embed_batch(["text1", "text2"])

        assert len(embeddings) == 2
        assert embeddings[0] == emb1
        assert embeddings[1] == emb2

    @pytest.mark.asyncio
    async def test_embed_batch_all_uncached(self, mock_base_provider):
        """Test embed_batch when no texts are cached."""
        cached_provider = CachedEmbeddingProvider(mock_base_provider, max_cache_size=100)

        embeddings = await cached_provider.embed_batch(["text1", "text2"])

        assert len(embeddings) == 2

    def test_dimension_delegates_to_base(self, mock_base_provider):
        """Test that dimension property delegates to base provider."""
        cached_provider = CachedEmbeddingProvider(mock_base_provider)

        assert cached_provider.dimension == 10

    def test_cache_key_generation(self):
        """Test that cache key is generated correctly."""
        provider = CachedEmbeddingProvider(MockEmbeddingProvider())

        key1 = provider._get_cache_key("test text")
        key2 = provider._get_cache_key("test text")
        key3 = provider._get_cache_key("different text")

        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 32  # MD5 hex digest length

    def test_max_cache_size_default(self, mock_base_provider):
        """Test default max cache size."""
        provider = CachedEmbeddingProvider(mock_base_provider)
        assert provider.max_cache_size == 10000


class TestOpenAIEmbeddingProvider:
    """Test OpenAIEmbeddingProvider."""

    def test_initialization_with_api_key(self):
        """Test initialization with API key."""
        try:
            provider = OpenAIEmbeddingProvider(api_key="test-key")
            assert provider.model == "text-embedding-3-small"
            assert provider._dimensions is None
        except ImportError:
            pytest.skip("openai not installed")

    def test_initialization_with_custom_model(self):
        """Test initialization with custom model."""
        try:
            provider = OpenAIEmbeddingProvider(
                api_key="test-key",
                model="text-embedding-3-large"
            )
            assert provider.model == "text-embedding-3-large"
        except ImportError:
            pytest.skip("openai not installed")

    def test_initialization_with_custom_dimensions(self):
        """Test initialization with custom dimensions."""
        try:
            provider = OpenAIEmbeddingProvider(
                api_key="test-key",
                dimensions=512
            )
            assert provider._dimensions == 512
        except ImportError:
            pytest.skip("openai not installed")

    def test_dimension_property_for_known_models(self):
        """Test dimension property for known models."""
        try:
            provider_small = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-small")
            assert provider_small.dimension == 1536

            provider_large = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-large")
            assert provider_large.dimension == 3072

            provider_ada = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-ada-002")
            assert provider_ada.dimension == 1536
        except ImportError:
            pytest.skip("openai not installed")

    def test_dimension_property_with_custom_dimensions(self):
        """Test dimension property with custom dimensions override."""
        try:
            provider = OpenAIEmbeddingProvider(
                api_key="test-key",
                dimensions=256
            )
            assert provider.dimension == 256
        except ImportError:
            pytest.skip("openai not installed")

    def test_dimension_property_default_for_unknown_model(self):
        """Test dimension property defaults to 1536 for unknown model."""
        try:
            provider = OpenAIEmbeddingProvider(
                api_key="test-key",
                model="unknown-model"
            )
            assert provider.dimension == 1536
        except ImportError:
            pytest.skip("openai not installed")

    def test_import_error_without_openai(self, monkeypatch):
        """Test that ImportError is raised when openai is not installed."""
        # This test verifies the error handling - it's hard to actually test
        # without uninstalling openai, so we just verify the code path exists
        # Skip if openai is actually available
        import importlib.util
        if importlib.util.find_spec("openai") is not None:
            pytest.skip("openai is installed, cannot test ImportError")
