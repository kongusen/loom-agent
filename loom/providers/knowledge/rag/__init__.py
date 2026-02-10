"""
RAG 框架原子能力

提供完整的 RAG 构建和检索能力，支持快速配置和灵活组合。

架构层次：
- L1 数据模型层 (models/): TextChunk, Entity, Relation, RetrievalResult
- L2 存储层 (stores/): ChunkStore, EntityStore, RelationStore
- L3 检索层 (retrievers/): VectorRetriever, GraphRetriever, KeywordRetriever
- L4 策略层 (strategies/): GraphFirstStrategy, VectorFirstStrategy, HybridStrategy
- L5 构建层 (builders/): RAGIndexBuilder, Chunker, EntityExtractor

快速使用：
    # 最简配置
    from loom.providers.knowledge.rag import GraphRAGKnowledgeBase

    kb = GraphRAGKnowledgeBase.from_config()
    await kb.add_texts(["文档内容1", "文档内容2"])
    results = await kb.query("查询问题")

    # 带 Embedding
    kb = GraphRAGKnowledgeBase.from_config(
        embedding_provider=your_embedding_provider,
    )

    # 完整配置
    from loom.providers.knowledge.rag import RAGConfig

    kb = GraphRAGKnowledgeBase.from_config(
        config=RAGConfig(
            strategy="graph_first",
            n_hop=2,
            chunk_size=512,
        ),
        embedding_provider=your_embedding_provider,
    )

    # 集成到 Agent
    agent = Agent.create(
        llm=llm,
        knowledge_base=kb,
    )
"""

# 主类
from loom.providers.knowledge.rag.graph_rag import GraphRAGKnowledgeBase

# 配置
from loom.providers.knowledge.rag.config import RAGConfig, StorageType

# 数据模型
from loom.providers.knowledge.rag.models import (
    Entity,
    Relation,
    RetrievalResult,
    TextChunk,
)

# 构建器
from loom.providers.knowledge.rag.builders import (
    ChunkingStrategy,
    Document,
    EntityExtractor,
    IndexBuilder,
    RAGIndexBuilder,
    SimpleChunker,
    SimpleEntityExtractor,
    SlidingWindowChunker,
)

# 策略
from loom.providers.knowledge.rag.strategies import (
    GraphFirstStrategy,
    HybridStrategy,
    RetrievalStrategy,
    StrategyType,
    VectorFirstStrategy,
)

# 检索器
from loom.providers.knowledge.rag.retrievers import (
    BaseRetriever,
    GraphRetriever,
    KeywordRetriever,
    VectorRetriever,
)

# 存储
from loom.providers.knowledge.rag.stores import (
    BaseStore,
    ChunkStore,
    EntityStore,
    InMemoryChunkStore,
    InMemoryEntityStore,
    InMemoryRelationStore,
    RelationStore,
)

__all__ = [
    # 主类
    "GraphRAGKnowledgeBase",
    # 配置
    "RAGConfig",
    "StorageType",
    # 数据模型
    "TextChunk",
    "Entity",
    "Relation",
    "RetrievalResult",
    # 构建器
    "IndexBuilder",
    "RAGIndexBuilder",
    "ChunkingStrategy",
    "SimpleChunker",
    "SlidingWindowChunker",
    "EntityExtractor",
    "SimpleEntityExtractor",
    "Document",
    # 策略
    "StrategyType",
    "RetrievalStrategy",
    "GraphFirstStrategy",
    "VectorFirstStrategy",
    "HybridStrategy",
    # 检索器
    "BaseRetriever",
    "VectorRetriever",
    "GraphRetriever",
    "KeywordRetriever",
    # 存储
    "BaseStore",
    "ChunkStore",
    "InMemoryChunkStore",
    "EntityStore",
    "InMemoryEntityStore",
    "RelationStore",
    "InMemoryRelationStore",
]
