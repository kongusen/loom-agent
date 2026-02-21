"""
GraphRAG 知识库主类

实现 KnowledgeBaseProvider 接口，提供完整的 RAG 能力
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem

if TYPE_CHECKING:
    from loom.observability.metrics import LoomMetrics
    from loom.observability.tracing import LoomTracer

from loom.providers.knowledge.rag.builders.base import Document, IndexBuilder
from loom.providers.knowledge.rag.builders.chunker import ChunkingStrategy, SlidingWindowChunker
from loom.providers.knowledge.rag.builders.entity_extractor import (
    EntityExtractor,
    LLMEntityExtractor,
)
from loom.providers.knowledge.rag.builders.index_builder import RAGIndexBuilder
from loom.providers.knowledge.rag.config import RAGConfig
from loom.providers.knowledge.rag.retrievers.graph import GraphRetriever
from loom.providers.knowledge.rag.retrievers.vector import VectorRetriever
from loom.providers.knowledge.rag.stores.chunk_store import ChunkStore, InMemoryChunkStore
from loom.providers.knowledge.rag.stores.entity_store import InMemoryEntityStore
from loom.providers.knowledge.rag.stores.relation_store import InMemoryRelationStore
from loom.providers.knowledge.rag.strategies.base import RetrievalStrategy
from loom.providers.knowledge.rag.strategies.graph_first import GraphFirstStrategy
from loom.providers.knowledge.rag.strategies.hybrid import HybridStrategy
from loom.providers.knowledge.rag.strategies.vector_first import VectorFirstStrategy

logger = logging.getLogger(__name__)


class GraphRAGKnowledgeBase(KnowledgeBaseProvider):
    """
    图增强 RAG 知识库

    实现 KnowledgeBaseProvider 接口，可直接用于 Agent.create()

    特点：
    - 支持多种检索策略（图优先、向量优先、混合）
    - LLM 和 Embedding 从 Agent 共享，不独立配置
    - 实体/关系提取用 LLM + ExtractionConfig（Skill 模式）
    - 三个内部 Store 保留为实现细节，外部统一为一个配置点
    """

    def __init__(
        self,
        strategy: RetrievalStrategy,
        chunk_store: ChunkStore,
        index_builder: IndexBuilder | None = None,
        name: str = "",
        description: str = "",
        search_hints: list[str] | None = None,
        supported_filters: list[str] | None = None,
        tracer: LoomTracer | None = None,
        metrics: LoomMetrics | None = None,
    ):
        self.strategy = strategy
        self.chunk_store = chunk_store
        self.index_builder = index_builder
        self._name = name
        self._description = description
        self._search_hints = search_hints or []
        self._supported_filters = supported_filters or []
        self.tracer = tracer
        self.metrics = metrics

    # ==================== KnowledgeBaseProvider 元信息 ====================

    @property
    def name(self) -> str:
        return self._name or "graph_rag"

    @property
    def description(self) -> str:
        return self._description or "GraphRAG knowledge base"

    @property
    def search_hints(self) -> list[str]:
        return self._search_hints

    @property
    def supported_filters(self) -> list[str]:
        return self._supported_filters

    # ==================== KnowledgeBaseProvider 接口实现 ====================

    async def query(
        self,
        query: str,
        limit: int = 5,
        _filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]:
        """查询知识库"""
        t0 = time.monotonic()

        # 如果有 tracer，包裹在 KNOWLEDGE_SEARCH span 中
        if self.tracer:
            from loom.observability.tracing import SpanKind

            with self.tracer.start_span(
                SpanKind.KNOWLEDGE_SEARCH,
                f"knowledge.query:{self.name}",
                attributes={"query": query, "limit": limit, "source": self.name},
            ):
                result = await self.strategy.retrieve(query, limit)
        else:
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

        # 记录指标
        if self.metrics:
            from loom.observability.metrics import LoomMetrics

            elapsed_ms = (time.monotonic() - t0) * 1000
            self.metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
            self.metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, elapsed_ms)
            self.metrics.set_gauge(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, len(items))

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
        """添加文档并构建索引"""
        if not self.index_builder:
            raise RuntimeError(
                "IndexBuilder not configured. Use from_config() to create with builder."
            )
        await self.index_builder.add_documents(documents, extract_entities)

    async def add_document(
        self,
        document: Document,
        extract_entities: bool = True,
    ) -> None:
        """添加单个文档"""
        if not self.index_builder:
            raise RuntimeError(
                "IndexBuilder not configured. Use from_config() to create with builder."
            )
        await self.index_builder.add_document(document, extract_entities)

    async def add_texts(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        extract_entities: bool = True,
    ) -> None:
        """便捷方法：直接添加文本列表"""
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
        llm_provider: Any | None = None,
        chunker: ChunkingStrategy | None = None,
        entity_extractor: EntityExtractor | None = None,
        name: str = "",
        description: str = "",
        search_hints: list[str] | None = None,
        supported_filters: list[str] | None = None,
        tracer: LoomTracer | None = None,
        metrics: LoomMetrics | None = None,
    ) -> GraphRAGKnowledgeBase:
        """
        从配置创建 GraphRAG 知识库（推荐方式）

        Args:
            config: RAG 配置
            embedding_provider: Embedding 提供者（从 Agent 共享）
            llm_provider: LLM 提供者（从 Agent 共享，用于实体提取）
            chunker: 分块策略（高级覆盖）
            entity_extractor: 实体抽取器（高级覆盖）
            name: 知识库标识名
            description: 知识库描述
            search_hints: 搜索提示
            supported_filters: 支持的过滤维度
            tracer: 追踪器（从 Agent 共享）
            metrics: 指标收集器（从 Agent 共享）

        Example:
            kb = GraphRAGKnowledgeBase.from_config(
                llm_provider=llm,
                embedding_provider=embedder,
                config=RAGConfig(
                    extraction=ExtractionConfig(
                        entity_types=["技术概念", "API端点"],
                        hints="关注技术架构",
                    ),
                ),
                name="product_docs",
                description="产品文档",
                search_hints=["产品功能", "API用法"],
            )
        """
        config = config or RAGConfig()

        # 1. 创建存储层（InMemory 默认，用户可通过子类扩展）
        chunk_store = InMemoryChunkStore()
        entity_store = InMemoryEntityStore()
        relation_store = InMemoryRelationStore()

        # 2. 创建检索器
        vector_retriever = None
        if embedding_provider:
            vector_retriever = VectorRetriever(chunk_store, embedding_provider)

        graph_retriever = GraphRetriever(entity_store, relation_store, chunk_store)

        # 3. 决定实体提取器
        if entity_extractor is None and llm_provider is not None and config.extraction.enabled:
            entity_extractor = LLMEntityExtractor(llm_provider, config.extraction)

        # 4. 创建策略（根据可用能力自动选择）
        strategy = cls._create_strategy(
            config,
            graph_retriever,
            vector_retriever,
            entity_extractor,
            tracer=tracer,
            metrics=metrics,
        )

        # 5. 创建索引构建器
        chunker = chunker or SlidingWindowChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

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
            name=name,
            description=description,
            search_hints=search_hints,
            supported_filters=supported_filters,
            tracer=tracer,
            metrics=metrics,
        )

    # ==================== 私有辅助方法 ====================

    @classmethod
    def _create_strategy(
        cls,
        config: RAGConfig,
        graph_retriever: GraphRetriever,
        vector_retriever: VectorRetriever | None,
        entity_extractor: EntityExtractor | None,
        tracer: LoomTracer | None = None,
        metrics: LoomMetrics | None = None,
    ) -> RetrievalStrategy:
        """
        根据配置和可用能力创建检索策略

        策略选择逻辑：
        - 有 embedding + 有 entity_extractor → 用户配置的策略（默认 hybrid）
        - 有 embedding + 无 entity_extractor → 自动降级为 vector_first
        - 无 embedding + 有 entity_extractor → graph_only
        - 无 embedding + 无 entity_extractor → graph_only（纯关键词）
        """
        has_vector = vector_retriever is not None
        has_extraction = entity_extractor is not None

        # 无 embedding → 只能用图检索
        if not has_vector:
            return _GraphOnlyStrategy(graph_retriever, config.n_hop)

        # 有 embedding 但无实体提取 → 降级为 vector_first
        if not has_extraction:
            if config.strategy != "vector_first":
                logger.info(
                    "No entity extractor available, auto-degrading strategy from '%s' to 'vector_first'",
                    config.strategy,
                )
            assert vector_retriever is not None  # guarded by has_vector check above
            return VectorFirstStrategy(
                vector_retriever=vector_retriever,
                threshold=config.vector_threshold,
            )

        # 有 embedding + 有实体提取 → 按用户配置
        assert vector_retriever is not None  # guarded by has_vector check above

        if config.strategy == "vector_first":
            return VectorFirstStrategy(
                vector_retriever=vector_retriever,
                threshold=config.vector_threshold,
            )

        if config.strategy == "hybrid":
            return HybridStrategy(
                graph_retriever=graph_retriever,
                vector_retriever=vector_retriever,
                n_hop=config.n_hop,
                graph_weight=config.graph_weight,
                vector_weight=config.vector_weight,
                tracer=tracer,
                metrics=metrics,
            )

        # 默认：graph_first
        return GraphFirstStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            n_hop=config.n_hop,
            tracer=tracer,
            metrics=metrics,
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

    async def retrieve(self, query: str, limit: int = 10, **_kwargs):
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
