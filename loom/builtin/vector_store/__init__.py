"""
Vector Store - Vector database adapters for RAG

Provides vector storage backends for semantic search:
- InMemoryVectorStore: Zero-config NumPy/FAISS-based storage
- ChromaDBAdapter: ChromaDB integration (optional)
"""

from loom.builtin.vector_store.in_memory_vector_store import (
    InMemoryVectorStore,
    VectorEntry,
)

__all__ = [
    "InMemoryVectorStore",
    "VectorEntry",
]
