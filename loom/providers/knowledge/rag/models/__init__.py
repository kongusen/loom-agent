"""
RAG 数据模型

定义 RAG 系统中的核心数据结构
"""

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.models.entity import Entity
from loom.providers.knowledge.rag.models.relation import Relation
from loom.providers.knowledge.rag.models.result import RetrievalResult

__all__ = [
    "TextChunk",
    "Entity",
    "Relation",
    "RetrievalResult",
]
