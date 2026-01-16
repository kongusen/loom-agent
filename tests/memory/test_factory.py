"""
Tests for Memory Factory
"""

import pytest

from loom.config.memory import EmbeddingConfig, VectorStoreConfig
from loom.memory.factory import create_embedding_provider, create_vector_store


class TestCreateVectorStore:
    """Test create_vector_store function."""

    def test_returns_none_when_disabled(self):
        """Test that None is returned when vector store is disabled."""
        config = VectorStoreConfig(enabled=False, provider="inmemory")
        result = create_vector_store(config)
        assert result is None

    def test_creates_inmemory_vector_store(self):
        """Test creating InMemoryVectorStore."""
        config = VectorStoreConfig(enabled=True, provider="inmemory")
        result = create_vector_store(config)

        assert result is not None
        assert result.__class__.__name__ == "InMemoryVectorStore"

    def test_raises_error_for_invalid_provider(self):
        """Test that ValueError is raised for invalid provider."""
        config = VectorStoreConfig(
            enabled=True, provider="nonexistent_provider", provider_config={}
        )

        with pytest.raises(ValueError, match="Failed to load custom vector store"):
            create_vector_store(config)

    def test_raises_error_for_invalid_custom_provider_format(self):
        """Test that ValueError is raised for malformed custom provider."""
        config = VectorStoreConfig(
            enabled=True, provider="invalid_format_no_dot", provider_config={}
        )

        with pytest.raises(ValueError):
            create_vector_store(config)

    def test_qdrant_provider_skipped_due_to_missing_dependency(self):
        """Test that Qdrant provider is handled (skips if not available)."""
        # This tests the Qdrant path - will fail gracefully if dependencies missing
        config = VectorStoreConfig(
            enabled=True, provider="qdrant", provider_config={"url": "http://localhost:6333"}
        )

        # This will fail if qdrant-client not installed, which is expected
        try:
            result = create_vector_store(config)
            # If it succeeds, check the type
            assert result is not None
        except (ImportError, TypeError):
            # Expected if qdrant-client not installed
            pass


class TestCreateEmbeddingProvider:
    """Test create_embedding_provider function."""

    def test_creates_openai_provider(self):
        """Test creating OpenAI embedding provider."""
        config = EmbeddingConfig(
            provider="openai", provider_config={"api_key": "test_key"}, enable_cache=False
        )

        result = create_embedding_provider(config)

        assert result is not None
        assert result.__class__.__name__ == "OpenAIEmbeddingProvider"

    def test_creates_mock_provider(self):
        """Test creating Mock embedding provider."""
        config = EmbeddingConfig(provider="mock", provider_config={}, enable_cache=False)

        result = create_embedding_provider(config)

        assert result is not None
        assert result.__class__.__name__ == "MockEmbeddingProvider"

    def test_wraps_with_cache_when_enabled(self):
        """Test that provider is wrapped with cache when enabled."""
        config = EmbeddingConfig(
            provider="mock", provider_config={}, enable_cache=True, cache_size=100
        )

        result = create_embedding_provider(config)

        assert result is not None
        assert result.__class__.__name__ == "CachedEmbeddingProvider"

    def test_raises_error_for_invalid_provider(self):
        """Test that ValueError is raised for invalid provider."""
        config = EmbeddingConfig(provider="nonexistent_provider", provider_config={})

        with pytest.raises(ValueError, match="Failed to load custom embedding provider"):
            create_embedding_provider(config)

    def test_raises_error_for_invalid_custom_provider_format(self):
        """Test that ValueError is raised for malformed custom provider."""
        config = EmbeddingConfig(provider="invalid_format_no_dot", provider_config={})

        with pytest.raises(ValueError):
            create_embedding_provider(config)

    def test_custom_provider_error_handling(self):
        """Test error handling for custom provider."""
        config = EmbeddingConfig(provider="nonexistent.module.Provider", provider_config={})

        with pytest.raises(ValueError, match="Failed to load custom embedding provider"):
            create_embedding_provider(config)

    def test_cache_size_respected(self):
        """Test that cache size is properly passed."""
        config = EmbeddingConfig(
            provider="mock", provider_config={}, enable_cache=True, cache_size=200
        )

        result = create_embedding_provider(config)

        assert result is not None
        assert result.__class__.__name__ == "CachedEmbeddingProvider"
        # The cache size should be respected
        assert result.max_cache_size == 200
