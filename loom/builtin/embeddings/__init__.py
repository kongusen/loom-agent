"""内置 Embedding 实现"""

from loom.builtin.embeddings.openai_embedding import OpenAIEmbedding

try:
    from loom.builtin.embeddings.sentence_transformers_embedding import SentenceTransformersEmbedding
    __all__ = ["OpenAIEmbedding", "SentenceTransformersEmbedding"]
except ImportError:
    __all__ = ["OpenAIEmbedding"]
