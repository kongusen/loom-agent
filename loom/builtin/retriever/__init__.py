"""内置检索器实现"""

from loom.builtin.retriever.in_memory import InMemoryRetriever

try:
    from loom.builtin.retriever.vector_store import VectorStoreRetriever
    __all__ = ["InMemoryRetriever", "VectorStoreRetriever"]
except ImportError:
    __all__ = ["InMemoryRetriever"]
