"""
Phase 4 Observability & Infrastructure Tests

覆盖：
- SpanKind: KNOWLEDGE_SEARCH / KNOWLEDGE_RETRIEVAL
- LoomMetrics: 知识搜索指标常量
- AdaptiveBudgetManager: 检索预算比例验证
- Reranker: 跨源去重（含 MEMORY origin）
"""

from loom.context.budget import (
    PHASE_ALLOCATION_TEMPLATES,
    AdaptiveBudgetManager,
    TaskPhase,
)
from loom.context.retrieval.candidates import CandidateOrigin, RetrievalCandidate
from loom.context.retrieval.reranker import Reranker
from loom.observability.metrics import LoomMetrics
from loom.observability.tracing import LoomTracer, SpanKind

# ==================== SpanKind ====================


class TestSpanKindKnowledge:
    """SpanKind 知识检索枚举值"""

    def test_knowledge_search_exists(self):
        assert hasattr(SpanKind, "KNOWLEDGE_SEARCH")
        assert SpanKind.KNOWLEDGE_SEARCH.value == "knowledge.search"

    def test_knowledge_retrieval_exists(self):
        assert hasattr(SpanKind, "KNOWLEDGE_RETRIEVAL")
        assert SpanKind.KNOWLEDGE_RETRIEVAL.value == "knowledge.retrieval"

    def test_all_span_kinds(self):
        values = {k.value for k in SpanKind}
        assert "knowledge.search" in values
        assert "knowledge.retrieval" in values
        # 确保原有值未被破坏
        assert "agent.run" in values
        assert "llm.call" in values
        assert "tool.execution" in values

    def test_tracer_accepts_knowledge_spans(self):
        """LoomTracer 可以创建知识检索 span"""
        tracer = LoomTracer(agent_id="test")
        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "query") as span:
            span.set_attribute("query", "API认证")
        with tracer.start_span(SpanKind.KNOWLEDGE_RETRIEVAL, "passive") as span:
            span.set_attribute("candidates", 5)

        spans = tracer.completed_spans
        assert len(spans) == 2
        assert spans[0].kind == SpanKind.KNOWLEDGE_SEARCH
        assert spans[1].kind == SpanKind.KNOWLEDGE_RETRIEVAL

    def test_trace_summary_includes_knowledge_spans(self):
        tracer = LoomTracer(agent_id="test")
        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "q1"):
            pass
        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "q2"):
            pass
        with tracer.start_span(SpanKind.KNOWLEDGE_RETRIEVAL, "passive"):
            pass

        summary = tracer.get_trace_summary()
        assert summary["spans_by_kind"]["knowledge.search"] == 2
        assert summary["spans_by_kind"]["knowledge.retrieval"] == 1


# ==================== LoomMetrics ====================


class TestLoomMetricsKnowledge:
    """LoomMetrics 知识搜索指标"""

    def test_metric_constants_exist(self):
        assert LoomMetrics.KNOWLEDGE_SEARCH_TOTAL == "knowledge_search_total"
        assert LoomMetrics.KNOWLEDGE_SEARCH_LATENCY == "knowledge_search_latency_ms"
        assert LoomMetrics.KNOWLEDGE_HIT_RATE == "knowledge_hit_rate"
        assert LoomMetrics.KNOWLEDGE_RESULTS_COUNT == "knowledge_results_count"

    def test_increment_search_total(self):
        metrics = LoomMetrics(agent_id="test")
        metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
        metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
        snap = metrics.snapshot()
        assert snap["counters"]["knowledge_search_total"] == 2

    def test_observe_search_latency(self):
        metrics = LoomMetrics(agent_id="test")
        metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, 45.2)
        metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, 32.1)
        snap = metrics.snapshot()
        hist = snap["histograms"]["knowledge_search_latency_ms"]
        assert hist["count"] == 2
        assert hist["min"] == 32.1
        assert hist["max"] == 45.2

    def test_set_hit_rate_gauge(self):
        metrics = LoomMetrics(agent_id="test")
        metrics.set_gauge(LoomMetrics.KNOWLEDGE_HIT_RATE, 0.85)
        snap = metrics.snapshot()
        assert snap["gauges"]["knowledge_hit_rate"] == 0.85

    def test_increment_results_count(self):
        metrics = LoomMetrics(agent_id="test")
        metrics.observe(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, 3)
        metrics.observe(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, 5)
        snap = metrics.snapshot()
        hist = snap["histograms"]["knowledge_results_count"]
        assert hist["avg"] == 4.0

    def test_existing_metrics_unchanged(self):
        """确保原有指标常量未被破坏"""
        assert LoomMetrics.ITERATIONS_TOTAL == "agent_iterations_total"
        assert LoomMetrics.TOKEN_INPUT == "agent_token_input"
        assert LoomMetrics.TOOL_CALLS_TOTAL == "agent_tool_calls_total"
        assert LoomMetrics.DELEGATION_TOTAL == "agent_delegation_total"


# ==================== AdaptiveBudgetManager ====================


class TestBudgetRetrievalRatios:
    """验证检索预算比例符合设计文档"""

    def test_early_phase_retrieval_ratio(self):
        assert PHASE_ALLOCATION_TEMPLATES[TaskPhase.EARLY]["retrieval"] == 0.20

    def test_middle_phase_retrieval_ratio(self):
        assert PHASE_ALLOCATION_TEMPLATES[TaskPhase.MIDDLE]["retrieval"] == 0.20

    def test_late_phase_retrieval_ratio(self):
        assert PHASE_ALLOCATION_TEMPLATES[TaskPhase.LATE]["retrieval"] == 0.18

    def test_phase_transition_updates_ratios(self):
        """阶段切换后 allocation_ratios 更新"""
        from unittest.mock import MagicMock

        counter = MagicMock()
        mgr = AdaptiveBudgetManager(
            token_counter=counter,
            model_context_window=128000,
        )
        assert mgr.current_phase == TaskPhase.EARLY

        mgr.update_phase(current_iteration=15, max_iterations=30)
        assert mgr.current_phase == TaskPhase.MIDDLE
        assert "retrieval" in mgr.allocation_ratios

        mgr.update_phase(current_iteration=25, max_iterations=30)
        assert mgr.current_phase == TaskPhase.LATE

    def test_all_phases_have_retrieval(self):
        """所有阶段模板都包含 retrieval 键"""
        for phase, template in PHASE_ALLOCATION_TEMPLATES.items():
            assert "retrieval" in template, f"Phase {phase} missing retrieval"


# ==================== Reranker Dedup ====================


class TestRerankerDedup:
    """跨源去重验证（含 MEMORY origin）"""

    def test_dedup_same_content_different_origins(self):
        """相同内容不同来源被去重"""
        c1 = RetrievalCandidate(
            id="l4-1",
            content="OAuth2.0 认证方案",
            origin=CandidateOrigin.L4_SEMANTIC,
            vector_score=0.9,
        )
        c2 = RetrievalCandidate(
            id="rag-1",
            content="OAuth2.0 认证方案",
            origin=CandidateOrigin.RAG_KNOWLEDGE,
            vector_score=0.7,
        )
        reranker = Reranker()
        result = reranker.rerank([c1, c2], query="OAuth2.0")
        assert result.duplicates_removed == 1
        # 保留高分的
        assert result.candidates[0].id == "l4-1"

    def test_dedup_memory_origin(self):
        """MEMORY origin 参与去重"""
        c1 = RetrievalCandidate(
            id="mem-1",
            content="数据库连接池配置",
            origin=CandidateOrigin.MEMORY,
            vector_score=0.8,
        )
        c2 = RetrievalCandidate(
            id="l4-1",
            content="数据库连接池配置",
            origin=CandidateOrigin.L4_SEMANTIC,
            vector_score=0.6,
        )
        reranker = Reranker()
        result = reranker.rerank([c1, c2], query="数据库")
        assert result.duplicates_removed == 1
        assert result.candidates[0].origin == CandidateOrigin.MEMORY

    def test_no_dedup_different_content(self):
        """不同内容不被去重"""
        c1 = RetrievalCandidate(
            id="l4-1",
            content="OAuth2.0 认证",
            origin=CandidateOrigin.L4_SEMANTIC,
            vector_score=0.9,
        )
        c2 = RetrievalCandidate(
            id="mem-1",
            content="JWT Token 验证",
            origin=CandidateOrigin.MEMORY,
            vector_score=0.8,
        )
        reranker = Reranker()
        result = reranker.rerank([c1, c2], query="认证")
        assert result.duplicates_removed == 0
        assert len(result.candidates) == 2

    def test_three_way_dedup(self):
        """三源相同内容去重"""
        content = "API 限流策略"
        c1 = RetrievalCandidate(
            id="l4-1",
            content=content,
            origin=CandidateOrigin.L4_SEMANTIC,
            vector_score=0.7,
        )
        c2 = RetrievalCandidate(
            id="rag-1",
            content=content,
            origin=CandidateOrigin.RAG_KNOWLEDGE,
            vector_score=0.9,
        )
        c3 = RetrievalCandidate(
            id="mem-1",
            content=content,
            origin=CandidateOrigin.MEMORY,
            vector_score=0.5,
        )
        reranker = Reranker()
        result = reranker.rerank([c1, c2, c3], query="限流")
        assert result.duplicates_removed == 2
        assert len(result.candidates) == 1
        # 保留最高分的 (rag-1, 0.9)
        assert result.candidates[0].id == "rag-1"

    def test_dedup_disabled(self):
        """关闭去重时不去重"""
        content = "相同内容"
        c1 = RetrievalCandidate(
            id="a",
            content=content,
            origin=CandidateOrigin.L4_SEMANTIC,
            vector_score=0.9,
        )
        c2 = RetrievalCandidate(
            id="b",
            content=content,
            origin=CandidateOrigin.MEMORY,
            vector_score=0.8,
        )
        reranker = Reranker(dedup=False)
        result = reranker.rerank([c1, c2], query="内容")
        assert result.duplicates_removed == 0
        assert len(result.candidates) == 2
