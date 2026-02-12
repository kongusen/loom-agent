"""
HybridStrategy 图谱扩展 + 观测体系 测试
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.observability.metrics import LoomMetrics
from loom.observability.tracing import InMemoryExporter, LoomTracer, SpanKind
from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.models.entity import Entity
from loom.providers.knowledge.rag.models.relation import Relation
from loom.providers.knowledge.rag.models.result import RetrievalResult
from loom.providers.knowledge.rag.retrievers.graph import GraphRetriever
from loom.providers.knowledge.rag.retrievers.vector import VectorRetriever
from loom.providers.knowledge.rag.stores.chunk_store import InMemoryChunkStore
from loom.providers.knowledge.rag.stores.entity_store import InMemoryEntityStore
from loom.providers.knowledge.rag.stores.relation_store import InMemoryRelationStore
from loom.providers.knowledge.rag.strategies.graph_first import GraphFirstStrategy
from loom.providers.knowledge.rag.strategies.hybrid import HybridStrategy

# ==================== Fixtures ====================


def _chunk(cid: str, content: str = "text", entity_ids: list[str] | None = None) -> TextChunk:
    c = TextChunk(id=cid, content=content, document_id="doc_1")
    c.entity_ids = entity_ids or []
    return c


def _entity(eid: str, text: str, chunk_ids: list[str] | None = None) -> Entity:
    return Entity(id=eid, text=text, entity_type="CONCEPT", chunk_ids=chunk_ids or [])


def _relation(rid: str, src: str, tgt: str) -> Relation:
    return Relation(id=rid, source_id=src, target_id=tgt, relation_type="USES")


@pytest.fixture
def stores():
    """创建内存存储三件套"""
    return InMemoryChunkStore(), InMemoryEntityStore(), InMemoryRelationStore()


@pytest.fixture
async def populated_stores(stores):
    """
    填充测试数据：

    chunk_v1 (entity: E_A) --USES--> E_B (chunk_exp)
    chunk_v2 (no entities)
    chunk_g1 (graph hit)
    chunk_exp (expansion target, only reachable via E_B)
    """
    cs, es, rs = stores

    chunk_v1 = _chunk("chunk_v1", "vector hit 1", entity_ids=["E_A"])
    chunk_v2 = _chunk("chunk_v2", "vector hit 2")
    chunk_g1 = _chunk("chunk_g1", "graph hit 1")
    chunk_exp = _chunk("chunk_exp", "expansion target", entity_ids=["E_B"])

    for c in [chunk_v1, chunk_v2, chunk_g1, chunk_exp]:
        await cs.add(c)

    e_a = _entity("E_A", "ConceptA", chunk_ids=["chunk_v1"])
    e_b = _entity("E_B", "ConceptB", chunk_ids=["chunk_exp"])
    await es.add(e_a)
    await es.add(e_b)

    rel = _relation("R1", "E_A", "E_B")
    await rs.add(rel)

    return cs, es, rs


# ==================== Graph Expansion Tests ====================


class TestHybridGraphExpansion:
    @pytest.mark.asyncio
    async def test_expansion_discovers_new_chunks(self, populated_stores):
        """向量命中 chunk_v1 → E_A → USES → E_B → chunk_exp"""
        cs, es, rs = populated_stores

        graph_retriever = GraphRetriever(es, rs, cs)
        # mock graph retriever 返回 chunk_g1
        graph_retriever.retrieve = AsyncMock(return_value=([], [], [await cs.get("chunk_g1")]))

        # mock vector retriever 返回 chunk_v1, chunk_v2
        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[
            (await cs.get("chunk_v1"), 0.9),
            (await cs.get("chunk_v2"), 0.7),
        ])
        # 保留 stores 引用给 expansion 使用
        vector_retriever.entity_store = es

        strategy = HybridStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            graph_weight=0.5,
            vector_weight=0.5,
            expansion_weight=0.3,
        )

        result = await strategy.retrieve("test query", limit=10)

        chunk_ids = {c.id for c in result.chunks}
        # chunk_exp 应该通过图谱扩展被发现
        assert "chunk_exp" in chunk_ids
        # 原始的 graph 和 vector 命中也在
        assert "chunk_g1" in chunk_ids
        assert "chunk_v1" in chunk_ids
        assert "chunk_v2" in chunk_ids

    @pytest.mark.asyncio
    async def test_expansion_no_entity_ids_skips(self, stores):
        """向量命中的 chunk 没有 entity_ids 时跳过扩展"""
        cs, es, rs = stores
        chunk_v = _chunk("chunk_v", "no entities")
        await cs.add(chunk_v)

        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([], [], []))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[
            (chunk_v, 0.8),
        ])

        strategy = HybridStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
        )

        result = await strategy.retrieve("test", limit=10)

        assert len(result.chunks) == 1
        assert result.chunks[0].id == "chunk_v"

    @pytest.mark.asyncio
    async def test_expansion_deduplicates_with_existing(self, populated_stores):
        """扩展不重复已有的 graph/vector 命中"""
        cs, es, rs = populated_stores

        graph_retriever = GraphRetriever(es, rs, cs)
        # graph 已经命中了 chunk_exp
        graph_retriever.retrieve = AsyncMock(return_value=(
            [], [], [await cs.get("chunk_exp")]
        ))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[
            (await cs.get("chunk_v1"), 0.9),
        ])

        strategy = HybridStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            expansion_weight=0.3,
        )

        result = await strategy.retrieve("test", limit=10)

        # chunk_exp 只出现一次（graph 已覆盖，expansion 不重复添加）
        exp_count = sum(1 for c in result.chunks if c.id == "chunk_exp")
        assert exp_count == 1

    @pytest.mark.asyncio
    async def test_expansion_weight_affects_score(self, populated_stores):
        """扩展 chunk 的分数受 expansion_weight 控制"""
        cs, es, rs = populated_stores

        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([], [], []))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[
            (await cs.get("chunk_v1"), 0.9),
        ])

        strategy = HybridStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            expansion_weight=0.3,
        )

        result = await strategy.retrieve("test", limit=10)

        if "chunk_exp" in result.scores:
            # expansion chunk 的分数应该 <= expansion_weight
            assert result.scores["chunk_exp"] <= 0.3 + 0.01  # 小浮点容差

    @pytest.mark.asyncio
    async def test_expansion_entities_merged(self, populated_stores):
        """扩展发现的实体合并到结果中"""
        cs, es, rs = populated_stores

        e_a = await es.get_by_text("ConceptA")
        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([e_a], [], []))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[
            (await cs.get("chunk_v1"), 0.9),
        ])

        strategy = HybridStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
        )

        result = await strategy.retrieve("test", limit=10)

        entity_ids = {e.id for e in result.entities}
        # E_A 来自 graph，E_B 来自 expansion
        assert "E_A" in entity_ids
        assert "E_B" in entity_ids


# ==================== Observability Tests ====================


class TestHybridObservability:
    @pytest.mark.asyncio
    async def test_tracer_span_attributes(self, stores):
        """tracer 记录检索阶段的 span attributes"""
        cs, es, rs = stores
        chunk = _chunk("c1", "content")
        await cs.add(chunk)

        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([], [], [chunk]))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[(chunk, 0.8)])

        tracer = LoomTracer(agent_id="test", enabled=True)
        exporter = InMemoryExporter()
        tracer.add_exporter(exporter)

        strategy = HybridStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            tracer=tracer,
        )

        # 需要在 span 上下文中执行，strategy._record_metrics 读取 current_span
        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "test_query") as span:
            await strategy.retrieve("test", limit=5)

        # 验证 span attributes
        assert span.attributes["retrieval.strategy"] == "hybrid"
        assert "retrieval.graph_count" in span.attributes
        assert "retrieval.vector_count" in span.attributes
        assert "retrieval.expansion_count" in span.attributes
        assert "retrieval.total_ms" in span.attributes

    @pytest.mark.asyncio
    async def test_metrics_recorded(self, stores):
        """metrics 记录检索指标"""
        cs, es, rs = stores
        chunk = _chunk("c1", "content")
        await cs.add(chunk)

        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([], [], []))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[(chunk, 0.8)])

        metrics = LoomMetrics(agent_id="test", enabled=True)

        strategy = HybridStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            metrics=metrics,
        )

        await strategy.retrieve("test", limit=5)

        snapshot = metrics.snapshot()
        assert snapshot["counters"].get(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL, 0) == 1
        assert LoomMetrics.KNOWLEDGE_SEARCH_LATENCY in str(snapshot["histograms"])

    @pytest.mark.asyncio
    async def test_no_tracer_no_error(self, stores):
        """没有 tracer/metrics 时不报错"""
        cs, es, rs = stores
        chunk = _chunk("c1", "content")
        await cs.add(chunk)

        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([], [], []))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[(chunk, 0.8)])

        strategy = HybridStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            # 不传 tracer/metrics
        )

        result = await strategy.retrieve("test", limit=5)
        assert len(result.chunks) == 1


class TestGraphFirstObservability:
    @pytest.mark.asyncio
    async def test_tracer_records_strategy(self, stores):
        """GraphFirstStrategy tracer 记录策略类型"""
        cs, es, rs = stores
        chunk = _chunk("c1", "content")
        await cs.add(chunk)

        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([], [], [chunk]))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.embedding_provider = Mock()
        vector_retriever.embedding_provider.embed = AsyncMock(return_value=[0.1, 0.2])

        tracer = LoomTracer(agent_id="test", enabled=True)

        strategy = GraphFirstStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            tracer=tracer,
        )

        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "test") as span:
            await strategy.retrieve("test", limit=5)

        assert span.attributes["retrieval.strategy"] == "graph_first"
        assert span.attributes["retrieval.fallback_to_vector"] is False

    @pytest.mark.asyncio
    async def test_fallback_recorded(self, stores):
        """降级到向量检索时记录 fallback"""
        cs, es, rs = stores
        chunk = _chunk("c1", "content")
        await cs.add(chunk)

        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([], [], []))  # 图检索无结果

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[(chunk, 0.8)])

        tracer = LoomTracer(agent_id="test", enabled=True)

        strategy = GraphFirstStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            tracer=tracer,
        )

        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "test") as span:
            await strategy.retrieve("test", limit=5)

        assert span.attributes["retrieval.fallback_to_vector"] is True
        assert span.attributes["retrieval.graph_count"] == 0

    @pytest.mark.asyncio
    async def test_metrics_on_fallback(self, stores):
        """降级时也记录 metrics"""
        cs, es, rs = stores
        chunk = _chunk("c1", "content")
        await cs.add(chunk)

        graph_retriever = GraphRetriever(es, rs, cs)
        graph_retriever.retrieve = AsyncMock(return_value=([], [], []))

        vector_retriever = Mock(spec=VectorRetriever)
        vector_retriever.retrieve = AsyncMock(return_value=[(chunk, 0.8)])

        metrics = LoomMetrics(agent_id="test", enabled=True)

        strategy = GraphFirstStrategy(
            graph_retriever=graph_retriever,
            vector_retriever=vector_retriever,
            metrics=metrics,
        )

        await strategy.retrieve("test", limit=5)

        snapshot = metrics.snapshot()
        assert snapshot["counters"].get(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL, 0) == 1


class TestGraphRAGKnowledgeBaseObservability:
    @pytest.mark.asyncio
    async def test_query_creates_span(self):
        """GraphRAGKnowledgeBase.query() 创建 KNOWLEDGE_SEARCH span"""
        from loom.providers.knowledge.rag.graph_rag import GraphRAGKnowledgeBase

        tracer = LoomTracer(agent_id="test", enabled=True)
        exporter = InMemoryExporter()
        tracer.add_exporter(exporter)

        # mock strategy
        mock_strategy = Mock()
        mock_strategy.retrieve = AsyncMock(return_value=RetrievalResult(
            chunks=[_chunk("c1", "result")],
            scores={"c1": 0.9},
        ))

        kb = GraphRAGKnowledgeBase(
            strategy=mock_strategy,
            chunk_store=InMemoryChunkStore(),
            name="test_kb",
            tracer=tracer,
        )

        items = await kb.query("test query", limit=5)

        assert len(items) == 1
        # 验证 span 被创建
        assert len(exporter.spans) == 1
        span = exporter.spans[0]
        assert span.kind == SpanKind.KNOWLEDGE_SEARCH
        assert "test_kb" in span.name
        assert span.attributes["query"] == "test query"

    @pytest.mark.asyncio
    async def test_query_records_metrics(self):
        """GraphRAGKnowledgeBase.query() 记录 metrics"""
        from loom.providers.knowledge.rag.graph_rag import GraphRAGKnowledgeBase

        metrics = LoomMetrics(agent_id="test", enabled=True)

        mock_strategy = Mock()
        mock_strategy.retrieve = AsyncMock(return_value=RetrievalResult(
            chunks=[_chunk("c1", "result"), _chunk("c2", "result2")],
            scores={"c1": 0.9, "c2": 0.7},
        ))

        kb = GraphRAGKnowledgeBase(
            strategy=mock_strategy,
            chunk_store=InMemoryChunkStore(),
            metrics=metrics,
        )

        await kb.query("test", limit=5)

        snapshot = metrics.snapshot()
        assert snapshot["counters"][LoomMetrics.KNOWLEDGE_SEARCH_TOTAL] == 1
        assert snapshot["gauges"][LoomMetrics.KNOWLEDGE_RESULTS_COUNT] == 2

    @pytest.mark.asyncio
    async def test_from_config_passes_tracer_metrics(self):
        """from_config 将 tracer/metrics 传递到策略"""
        from loom.providers.knowledge.rag.config import RAGConfig
        from loom.providers.knowledge.rag.graph_rag import GraphRAGKnowledgeBase

        tracer = LoomTracer(agent_id="test")
        metrics = LoomMetrics(agent_id="test")

        mock_embedder = Mock()
        mock_llm = Mock()

        kb = GraphRAGKnowledgeBase.from_config(
            config=RAGConfig(strategy="hybrid"),
            embedding_provider=mock_embedder,
            llm_provider=mock_llm,
            tracer=tracer,
            metrics=metrics,
        )

        assert kb.tracer is tracer
        assert kb.metrics is metrics
        # HybridStrategy 也应该拿到 tracer/metrics
        assert kb.strategy.tracer is tracer
        assert kb.strategy.metrics is metrics
