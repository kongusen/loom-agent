"""
Phase 5 Wiring Integration Tests

验证所有基础设施模块已正确接入 Agent 主流程：
- LoomTracer / LoomMetrics 在 Agent 中创建并使用
- AdaptiveBudgetManager 替代 BudgetManager
- Reranker 接入 UnifiedSearchExecutor
- 知识搜索路径有 span/metrics 埋点
- ContextOrchestrator 支持外部注入 budget_manager
"""

from unittest.mock import MagicMock

from loom.context.budget import AdaptiveBudgetManager, BudgetManager
from loom.context.orchestrator import ContextOrchestrator
from loom.context.retrieval.reranker import Reranker
from loom.observability.metrics import LoomMetrics
from loom.observability.tracing import LoomTracer, SpanKind
from loom.tools.search.executor import UnifiedSearchExecutor

# ==================== Agent Observability Wiring ====================


class TestAgentObservabilityWiring:
    """验证 Agent 创建了 LoomTracer 和 LoomMetrics"""

    def _make_agent(self, **kwargs):
        from loom.agent import Agent
        from loom.providers.llm.mock import MockLLMProvider

        defaults = {
            "node_id": "test-agent",
            "llm_provider": MockLLMProvider(responses=[]),
            "max_context_tokens": 4000,
        }
        defaults.update(kwargs)
        return Agent(**defaults)

    def test_agent_has_tracer(self):
        agent = self._make_agent()
        assert hasattr(agent, "_tracer")
        assert isinstance(agent._tracer, LoomTracer)
        assert agent._tracer.agent_id == "test-agent"

    def test_agent_has_metrics(self):
        agent = self._make_agent()
        assert hasattr(agent, "_metrics")
        assert isinstance(agent._metrics, LoomMetrics)
        assert agent._metrics.agent_id == "test-agent"

    def test_tracer_enabled_by_default(self):
        agent = self._make_agent()
        assert agent._tracer.enabled is True

    def test_tracer_disabled_when_observation_off(self):
        agent = self._make_agent(enable_observation=False)
        assert agent._tracer.enabled is False

    def test_metrics_disabled_when_observation_off(self):
        agent = self._make_agent(enable_observation=False)
        assert agent._metrics.enabled is False


# ==================== AdaptiveBudgetManager Wiring ====================


class TestAdaptiveBudgetWiring:
    """验证 Agent 使用 AdaptiveBudgetManager 而非 BudgetManager"""

    def _make_agent(self, **kwargs):
        from loom.agent import Agent
        from loom.providers.llm.mock import MockLLMProvider

        defaults = {
            "node_id": "test-agent",
            "llm_provider": MockLLMProvider(responses=[]),
            "max_context_tokens": 4000,
        }
        defaults.update(kwargs)
        return Agent(**defaults)

    def test_agent_has_adaptive_budget(self):
        agent = self._make_agent()
        assert hasattr(agent, "_adaptive_budget")
        assert isinstance(agent._adaptive_budget, AdaptiveBudgetManager)

    def test_orchestrator_uses_adaptive_budget(self):
        agent = self._make_agent()
        # ContextOrchestrator 的 budget_manager 应该是 AdaptiveBudgetManager
        assert isinstance(
            agent.context_orchestrator.budget_manager,
            AdaptiveBudgetManager,
        )

    def test_adaptive_budget_is_same_instance(self):
        """Agent._adaptive_budget 和 orchestrator.budget_manager 是同一实例"""
        agent = self._make_agent()
        assert agent._adaptive_budget is agent.context_orchestrator.budget_manager


class TestContextOrchestratorBudgetInjection:
    """验证 ContextOrchestrator 支持外部注入 budget_manager"""

    def test_default_creates_budget_manager(self):
        counter = MagicMock()
        orch = ContextOrchestrator(
            token_counter=counter,
            sources=[],
            model_context_window=4000,
        )
        assert isinstance(orch.budget_manager, BudgetManager)

    def test_injected_budget_manager_used(self):
        counter = MagicMock()
        adaptive = AdaptiveBudgetManager(
            token_counter=counter,
            model_context_window=4000,
        )
        orch = ContextOrchestrator(
            token_counter=counter,
            sources=[],
            model_context_window=4000,
            budget_manager=adaptive,
        )
        assert orch.budget_manager is adaptive
        assert isinstance(orch.budget_manager, AdaptiveBudgetManager)


# ==================== Reranker Wiring ====================


class TestRerankerWiring:
    """验证 Reranker 接入 UnifiedSearchExecutor"""

    def test_executor_has_default_reranker(self):
        executor = UnifiedSearchExecutor()
        assert isinstance(executor._reranker, Reranker)

    def test_executor_accepts_custom_reranker(self):
        custom = Reranker(min_score_threshold=0.5)
        executor = UnifiedSearchExecutor(reranker=custom)
        assert executor._reranker is custom

    def test_executor_default_reranker_has_dedup(self):
        executor = UnifiedSearchExecutor()
        assert executor._reranker.dedup is True


# ==================== Metrics Recording ====================


class TestMetricsRecording:
    """验证 LoomMetrics 指标记录功能"""

    def test_iteration_metrics_increment(self):
        metrics = LoomMetrics(agent_id="test")
        metrics.increment(LoomMetrics.ITERATIONS_TOTAL)
        metrics.increment(LoomMetrics.ITERATIONS_TOTAL)
        snap = metrics.snapshot()
        assert snap["counters"]["agent_iterations_total"] == 2

    def test_tool_call_metrics_increment(self):
        metrics = LoomMetrics(agent_id="test")
        metrics.increment(LoomMetrics.TOOL_CALLS_TOTAL)
        snap = metrics.snapshot()
        assert snap["counters"]["agent_tool_calls_total"] == 1

    def test_knowledge_search_metrics(self):
        metrics = LoomMetrics(agent_id="test")
        metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
        metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, 50.0)
        metrics.observe(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, 3)
        metrics.set_gauge(LoomMetrics.KNOWLEDGE_HIT_RATE, 1.0)

        snap = metrics.snapshot()
        assert snap["counters"]["knowledge_search_total"] == 1
        assert snap["histograms"]["knowledge_search_latency_ms"]["count"] == 1
        assert snap["histograms"]["knowledge_results_count"]["avg"] == 3.0
        assert snap["gauges"]["knowledge_hit_rate"] == 1.0


# ==================== Tracing Spans ====================


class TestTracingSpans:
    """验证 LoomTracer span 创建"""

    def test_knowledge_search_span(self):
        tracer = LoomTracer(agent_id="test")
        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "test query") as span:
            span.set_attribute("scope", "auto")
            span.set_attribute("results_count", 3)

        spans = tracer.completed_spans
        assert len(spans) == 1
        assert spans[0].kind == SpanKind.KNOWLEDGE_SEARCH
        assert spans[0].name == "test query"
        assert spans[0].attributes["results_count"] == 3

    def test_trace_summary_after_search(self):
        tracer = LoomTracer(agent_id="test")
        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "q1"):
            pass
        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "q2"):
            pass

        summary = tracer.get_trace_summary()
        assert summary["span_count"] == 2
        assert summary["spans_by_kind"]["knowledge.search"] == 2

    def test_new_trace_resets(self):
        tracer = LoomTracer(agent_id="test")
        with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "q1"):
            pass
        assert len(tracer.completed_spans) == 1

        tracer.new_trace()
        assert len(tracer.completed_spans) == 0


# ==================== AdaptiveBudget Phase Updates ====================


class TestAdaptiveBudgetPhaseUpdates:
    """验证 AdaptiveBudgetManager 阶段更新"""

    def test_phase_updates_with_iteration(self):
        counter = MagicMock()
        mgr = AdaptiveBudgetManager(
            token_counter=counter,
            model_context_window=128000,
        )
        # 初始阶段
        assert mgr.current_phase == "early"

        # 中期
        mgr.update_phase(current_iteration=5, max_iterations=10)
        assert mgr.current_phase == "middle"

        # 后期
        mgr.update_phase(current_iteration=8, max_iterations=10)
        assert mgr.current_phase == "late"

    def test_phase_updates_allocation_ratios(self):
        counter = MagicMock()
        mgr = AdaptiveBudgetManager(
            token_counter=counter,
            model_context_window=128000,
        )
        early_ratios = dict(mgr.allocation_ratios)

        mgr.update_phase(current_iteration=8, max_iterations=10)
        late_ratios = dict(mgr.allocation_ratios)

        # 比例应该发生变化
        assert early_ratios != late_ratios
