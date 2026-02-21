"""
RAG 索引构建器实现
"""

from typing import Any

from loom.providers.knowledge.rag.builders.base import Document, IndexBuilder
from loom.providers.knowledge.rag.builders.chunker import ChunkingStrategy, SimpleChunker
from loom.providers.knowledge.rag.builders.entity_extractor import EntityExtractor
from loom.providers.knowledge.rag.stores.chunk_store import ChunkStore
from loom.providers.knowledge.rag.stores.entity_store import EntityStore
from loom.providers.knowledge.rag.stores.relation_store import RelationStore


class RAGIndexBuilder(IndexBuilder):
    """
    RAG 索引构建器

    完整的索引构建流程：
    1. 文档分块
    2. 生成 Embedding
    3. 实体抽取（可选，需要 entity_extractor）
    4. 存储到各个 Store
    """

    def __init__(
        self,
        chunk_store: ChunkStore,
        entity_store: EntityStore,
        relation_store: RelationStore,
        embedding_provider: Any | None = None,
        chunker: ChunkingStrategy | None = None,
        entity_extractor: EntityExtractor | None = None,
    ):
        self.chunk_store = chunk_store
        self.entity_store = entity_store
        self.relation_store = relation_store
        self.embedding_provider = embedding_provider
        self.chunker = chunker or SimpleChunker()
        self.entity_extractor = entity_extractor  # None = 跳过实体提取

    async def add_documents(
        self,
        documents: list[Document],
        extract_entities: bool = True,
    ) -> None:
        """批量添加文档"""
        for doc in documents:
            await self.add_document(doc, extract_entities)

    async def add_document(
        self,
        document: Document,
        extract_entities: bool = True,
    ) -> None:
        """添加单个文档"""
        # 1. 分块
        chunks = self.chunker.chunk(document)

        # 2. 生成 Embedding
        if self.embedding_provider:
            for chunk in chunks:
                chunk.embedding = await self.embedding_provider.embed(chunk.content)

        # 3. 实体抽取（需要 entity_extractor 且 extract_entities=True）
        if extract_entities and self.entity_extractor:
            for chunk in chunks:
                entities, relations = await self.entity_extractor.extract(chunk)

                # 更新 chunk 的 entity_ids
                chunk.entity_ids = [e.id for e in entities]

                # 存储实体和关系
                await self.entity_store.add_batch(entities)
                await self.relation_store.add_batch(relations)

        # 4. 存储 chunks
        await self.chunk_store.add_batch(chunks)

    async def clear(self) -> None:
        """清空索引"""
        await self.chunk_store.clear()
        await self.entity_store.clear()
        await self.relation_store.clear()
