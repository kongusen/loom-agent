"""
Embeddings - Text embedding models for vector search

Provides embedding adapters for converting text to vectors:
- OpenAIEmbedding: OpenAI embedding API
"""

from loom.builtin.embeddings.openai_embedding import OpenAIEmbedding

__all__ = [
    "OpenAIEmbedding",
]
