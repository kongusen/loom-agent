"""
GraphRAG 知识库主类

实现 KnowledgeBaseProvider 接口，提供完整的 RAG 能力
"""

from typing import Any

from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem
from loom.providers.knowledge.rag.builders.base import Document, IndexBuilder
from loom.providers.knowledge.rag.builders.chunker import ChunkingStrategy, SlidingWindowChunker
from loom.providers.knowledge.rag.builders.entity_extractor import EntityExtractor, SimpleEntityExtractor
from loom.providers.knowledge.rag.builders.index_builder import RAGIndexBuilder
from loom.providers.knowledge.rag.config import RAGConfig, StorageType
from loom.providers.knowledge.rag.retrievers.graph import GraphRetriever
from loom.providers.knowledge.rag.retrievers.vector import VectorRetriever
from loom.providers.knowledge.rag.stores.chunk_store import ChunkStore, InMemoryChunkStore
from loom.providers.knowledge.rag.stores.entity_store import EntityStore, InMemoryEntityStore
from loom.providers.knowledge.rag.stores.relation_store import InMemoryRelationStore, RelationStore
from loom.providers.knowledge.rag.strategies.base import RetrievalStrategy
from loom.providers.knowledge.rag.strategies.graph_first import GraphFirstStrategy
from loom.providers.knowledge.rag.strategies.hybrid import HybridStrategy
from loom.providers.knowledge.rag.strategies.vector_first import VectorFirstStrategy


class GraphRAGKnowledgeBase(KnowledgeBaseProvider):
    """
    图增强 RAG 知识库

    实现 KnowledgeBaseProvider 接口，可直接用于 Agent.create()

    特点：
    - 支持多种检索策略（图优先、向量优先、混合）
    - 提供快速配置工厂方法
    - 内置索引构建能力
    - 兼容现有 Agent 接口
    """

    def __init__(
        self,
        strategy: RetrievalStrategy,
        chunk_store: ChunkStore,
        index_builder: IndexBuilder | None = None,
    ):
        """
        初始化 GraphRAG 知识库

        Args:
            strategy: 检索策略
            chunk_store: 文本块存储
            index_builder: 索引构建器（可选）
        """
        self.strategy = strategy
        self.chunk_store = chunk_store
        self.index_builder = index_builder

    # ==================== KnowledgeBaseProvider 接口实现 ====================

    async def query(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]:
        """查询知识库"""
        result = await self.strategy.retrieve(query, limit)

        # 转换为 KnowledgeItem 格式
        items = []
        for chunk in result.chunks:
            score = result.scores.get(chunk.id, 0.0)
            items.append(
                KnowledgeItem(
                    id=chunk.id,
                    content=chunk.content,
                    source=chunk.document_id,
                    relevance=score,
                    metadata={
                        "entity_ids": chunk.entity_ids,
                        "keywords": chunk.keywords,
                        **chunk.metadata,
                    },
                )
            )
        return items

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        """根据ID获取知识条目"""
        chunk = await self.chunk_store.get(knowledge_id)
        if not chunk:
            return None
        return KnowledgeItem(
            id=chunk.id,
            content=chunk.content,
            source=chunk.document_id,
            metadata=chunk.metadata,
        )

    # ==================== 索引构建方法 ====================

    async def add_documents(
        self,
        documents: list[Document],
        extract_entities: bool = True,
    ) -> None:
        """
        添加文档并构建索引

        Args:
            documents: 文档列表
            extract_entities: 是否抽取实体
        """
        if not self.index_builder:
            raise RuntimeError("IndexBuilder not configured. Use from_config() to create with builder.")
        await self.index_builder.add_documents(documents, extract_entities)

    async def add_document(
        self,
        document: Document,
        extract_entities: bool = True,
    ) -> None:
        """添加单个文档"""
        if not self.index_builder:
            raise RuntimeError("IndexBuilder not configured. Use from_config() to create with builder.")
        await self.index_builder.add_document(document, extract_entities)

    async def add_texts(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        extract_entities: bool = True,
    ) -> None:
        """
        便捷方法：直接添加文本列表

        Args:
            texts: 文本列表
            metadatas: 元数据列表（可选）
            extract_entities: 是否抽取实体
        """
        import uuid
        documents = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            documents.append(
                Document(
                    id=f"doc_{uuid.uuid4().hex[:8]}",
                    content=text,
                    metadata=metadata,
                )
            )
        await self.add_documents(documents, extract_entities)

    # ==================== 工厂方法（快速配置） ====================

    @classmethod
    def from_config(
        cls,
        config: RAGConfig | None = None,
        embedding_provider: Any | None = None,
        chunker: ChunkingStrategy | None = None,
        entity_extractor: EntityExtractor | None = None,
    ) -> "GraphRAGKnowledgeBase":
        """
        从配置创建 GraphRAG 知识库（推荐方式）

        Args:
            config: RAG 配置，默认使用内存存储
            embedding_provider: Embedding 提供者
            chunker: 分块策略
            entity_extractor: 实体抽取器

        Returns:
            配置好的 GraphRAGKnowledgeBase 实例

        Example:
            # 最简配置
            kb = GraphRAGKnowledgeBase.from_config()

            # 带 embedding
            kb = GraphRAGKnowledgeBase.from_config(
                embedding_provider=openai_embedding,
            )

            # 完整配置
            kb = GraphRAGKnowledgeBase.from_config(
                config=RAGConfig(
                    strategy="graph_first",
                    n_hop=2,
                    chunk_size=512,
                ),
                embedding_provider=openai_embedding,
            )
        """
        config = config or RAGConfig()

        # 1. 创建存储层
        chunk_store, entity_store, relation_store = cls._create_stores(config)

        # 2. 创建检索器
        vector_retriever = None
        if embedding_provider:
            vector_retriever = VectorRetriever(chunk_store, embedding_provider)

        graph_retriever = GraphRetriever(entity_store, relation_store, chunk_store)

        # 3. 创建策略
        strategy = cls._create_strategy(
            config, graph_retriever, vector_retriever
        )

        # 4. 创建索引构建器
        chunker = chunker or SlidingWindowChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        entity_extractor = entity_extractor or SimpleEntityExtractor()

        index_builder = RAGIndexBuilder(
            chunk_store=chunk_store,
            entity_store=entity_store,
            relation_store=relation_store,
            embedding_provider=embedding_provider,
            chunker=chunker,
            entity_extractor=entity_extractor,
        )

        return cls(
            strategy=strategy,
            chunk_store=chunk_store,
            index_builder=index_builder,
        )

    # ==================== 私有辅助方法 ====================

    @classmethod
    def _create_stores(
        cls,
        config: RAGConfig,
    ) -> tuple[ChunkStore, EntityStore, RelationStore]:
        """根据配置创建存储层"""
        if config.storage_type == StorageType.MEMORY:
            return (
                InMemoryChunkStore(),
                InMemoryEntityStore(),
                InMemoryRelationStore(),
            )
        # 其他存储类型可在此扩展
        raise ValueError(f"Unsupported storage type: {config.storage_type}")

    @classmethod
    def _create_strategy(
        cls,
        config: RAGConfig,
        graph_retriever: GraphRetriever,
        vector_retriever: VectorRetriever | None,
    ) -> RetrievalStrategy:
        """根据配置创建检索策略"""
        if config.strategy == "vector_first":
            if not vector_retriever:
                raise ValueError("vector_first strategy requires embedding_provider")
            return VectorFirstStrategy(
                vector_retriever=vector_retriever,
                threshold=config.vector_threshold,
            )

        if config.strategy == "hybrid":
            if not vector_retriever:
                raise ValueError("hybrid strategy requires embedding_provider")
            return HybridStrategy(
                graph_retriever=graph_retriever,
                vector_retriever=vector_retriever,
                n_hop=config.n_hop,
                graph_weight=config.graph_weight,
                vector_weight=config.vector_weight,
            )

        # 默认：graph_first
        if not vector_retriever:
            # 无 embedding 时降级为纯图检索
            return _GraphOnlyStrategy(graph_retriever, config.n_hop)

        return GraphFirstStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            n_hop=config.n_hop,
        )


class _GraphOnlyStrategy(RetrievalStrategy):
    """
    纯图检索策略（内部使用）

    当没有 embedding_provider 时的降级策略
    """

    def __init__(self, graph_retriever: GraphRetriever, n_hop: int = 2):
        self.graph_retriever = graph_retriever
        self.n_hop = n_hop

    @property
    def strategy_type(self):
        from loom.providers.knowledge.rag.strategies.base import StrategyType
        return StrategyType.GRAPH_FIRST

    async def retrieve(self, query: str, limit: int = 10, **kwargs):
        from loom.providers.knowledge.rag.models.result import RetrievalResult

        entities, relations, chunks = await self.graph_retriever.retrieve(
            query, n_hop=self.n_hop, limit=limit
        )

        # 简单按位置排序
        scores = {c.id: 1.0 - (i / len(chunks)) for i, c in enumerate(chunks)} if chunks else {}

        return RetrievalResult(
            chunks=chunks,
            entities=entities,
            relations=relations,
            scores=scores,
        )
