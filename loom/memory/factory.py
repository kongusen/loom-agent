"""
Factory functions for creating vector stores and embedding providers.
"""
from typing import Optional
from loom.config.memory import VectorStoreConfig, EmbeddingConfig
from .vector_store import VectorStoreProvider
from .embedding import EmbeddingProvider


def create_vector_store(config: VectorStoreConfig) -> Optional[VectorStoreProvider]:
    """
    Create a vector store instance based on configuration.

    Args:
        config: Vector store configuration

    Returns:
        VectorStoreProvider instance or None if disabled
    """
    if not config.enabled:
        return None

    provider = config.provider.lower()

    if provider == "inmemory":
        from .vector_store import InMemoryVectorStore
        return InMemoryVectorStore()

    elif provider == "qdrant":
        from .vector_store import QdrantVectorStore
        return QdrantVectorStore(**config.provider_config)

    elif provider == "chroma":
        from .vector_store import ChromaVectorStore
        return ChromaVectorStore(**config.provider_config)

    else:
        # Custom provider: assume it's a class path
        # e.g., "mypackage.MyVectorStore"
        try:
            module_path, class_name = provider.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            provider_class = getattr(module, class_name)
            return provider_class(**config.provider_config)
        except Exception as e:
            raise ValueError(f"Failed to load custom vector store '{provider}': {e}")


def create_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    """
    Create an embedding provider instance based on configuration.

    Args:
        config: Embedding configuration

    Returns:
        EmbeddingProvider instance
    """
    provider = config.provider.lower()

    if provider == "openai":
        from .embedding import OpenAIEmbeddingProvider
        base_provider = OpenAIEmbeddingProvider(**config.provider_config)

    elif provider == "mock":
        from .embedding import MockEmbeddingProvider
        base_provider = MockEmbeddingProvider(**config.provider_config)

    else:
        # Custom provider
        try:
            module_path, class_name = provider.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            provider_class = getattr(module, class_name)
            base_provider = provider_class(**config.provider_config)
        except Exception as e:
            raise ValueError(f"Failed to load custom embedding provider '{provider}': {e}")

    # Wrap with cache if enabled
    if config.enable_cache:
        from .embedding import CachedEmbeddingProvider
        return CachedEmbeddingProvider(base_provider, max_cache_size=config.cache_size)

    return base_provider
