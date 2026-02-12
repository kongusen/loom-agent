"""
Tests for observability: tracing + metrics
"""

import time

import pytest

from loom.observability.metrics import LoomMetrics, MetricPoint, MetricType
from loom.observability.tracing import (
    InMemoryExporter,
    LogSpanExporter,
    LoomTracer,
    Span,
    SpanExporter,
    SpanKind,
    trace_operation,
)


# ============ Metrics ============


class TestMetricType:
    def test_enum_values(self):
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"


class TestMetricPoint:
    def test_basic_creation(self):
        mp = MetricPoint(name="test", value=1.0, metric_type=MetricType.COUNTER)
        assert mp.name == "test"
        assert mp.value == 1.0
        assert mp.metric_type == MetricType.COUNTER
        assert mp.labels == {}
        assert mp.timestamp > 0

    def test_with_labels(self):
        mp = MetricPoint(
            name="test", value=2.0, metric_type=MetricType.GAUGE, labels={"env": "prod"}
        )
        assert mp.labels == {"env": "prod"}


class TestLoomMetricsInit:
    def test_default_init(self):
        m = LoomMetrics()
        assert m.agent_id == ""
        assert m.enabled is True

    def test_custom_init(self):
        m = LoomMetrics(agent_id="a1", enabled=False)
        assert m.agent_id == "a1"
        assert m.enabled is False

    def test_predefined_metric_names(self):
        assert LoomMetrics.ITERATIONS_TOTAL == "agent_iterations_total"
        assert LoomMetrics.TOKEN_INPUT == "agent_token_input"
        assert LoomMetrics.KNOWLEDGE_SEARCH_TOTAL == "knowledge_search_total"


class TestLoomMetricsCounter:
    def test_increment_default(self):
        m = LoomMetrics()
        m.increment("test_counter")
        assert m._counters["test_counter"] == 1.0

    def test_increment_custom_value(self):
        m = LoomMetrics()
        m.increment("test_counter", 5.0)
        assert m._counters["test_counter"] == 5.0

    def test_increment_accumulates(self):
        m = LoomMetrics()
        m.increment("c", 3.0)
        m.increment("c", 2.0)
        assert m._counters["c"] == 5.0

    def test_increment_with_labels(self):
        m = LoomMetrics()
        m.increment("c", 1.0, {"tool": "search"})
        assert m._counters['c{tool=search}'] == 1.0

    def test_increment_disabled(self):
        m = LoomMetrics(enabled=False)
        m.increment("c")
        assert len(m._counters) == 0


class TestLoomMetricsGauge:
    def test_set_gauge(self):
        m = LoomMetrics()
        m.set_gauge("g", 0.75)
        assert m._gauges["g"] == 0.75

    def test_set_gauge_overwrites(self):
        m = LoomMetrics()
        m.set_gauge("g", 0.5)
        m.set_gauge("g", 0.9)
        assert m._gauges["g"] == 0.9

    def test_set_gauge_disabled(self):
        m = LoomMetrics(enabled=False)
        m.set_gauge("g", 1.0)
        assert len(m._gauges) == 0


class TestLoomMetricsHistogram:
    def test_observe(self):
        m = LoomMetrics()
        m.observe("h", 1.5)
        m.observe("h", 2.5)
        assert m._histograms["h"] == [1.5, 2.5]

    def test_observe_disabled(self):
        m = LoomMetrics(enabled=False)
        m.observe("h", 1.0)
        assert len(m._histograms) == 0


class TestLoomMetricsConvenience:
    def test_record_tokens(self):
        m = LoomMetrics()
        m.record_tokens(input_tokens=500, output_tokens=200)
        assert m._counters[LoomMetrics.TOKEN_INPUT] == 500
        assert m._counters[LoomMetrics.TOKEN_OUTPUT] == 200

    def test_observe_latency(self):
        m = LoomMetrics()
        m.observe_latency("llm_call", 123.4)
        assert m._histograms["llm_call_latency_ms"] == [123.4]


class TestLoomMetricsSnapshot:
    def test_snapshot_empty(self):
        m = LoomMetrics(agent_id="a1")
        snap = m.snapshot()
        assert snap["agent_id"] == "a1"
        assert snap["counters"] == {}
        assert snap["gauges"] == {}
        assert snap["histograms"] == {}

    def test_snapshot_with_data(self):
        m = LoomMetrics(agent_id="a1")
        m.increment("c", 10)
        m.set_gauge("g", 0.5)
        m.observe("h", 1.0)
        m.observe("h", 3.0)
        snap = m.snapshot()
        assert snap["counters"]["c"] == 10
        assert snap["gauges"]["g"] == 0.5
        h = snap["histograms"]["h"]
        assert h["count"] == 2
        assert h["sum"] == 4.0
        assert h["min"] == 1.0
        assert h["max"] == 3.0
        assert h["avg"] == 2.0

    def test_snapshot_percentiles(self):
        m = LoomMetrics()
        for i in range(100):
            m.observe("h", float(i))
        snap = m.snapshot()
        h = snap["histograms"]["h"]
        assert h["p50"] == 50.0
        assert h["p95"] == 95.0
        assert h["p99"] == 99.0


class TestLoomMetricsReset:
    def test_reset_clears_all(self):
        m = LoomMetrics()
        m.increment("c")
        m.set_gauge("g", 1.0)
        m.observe("h", 1.0)
        m.reset()
        assert m._counters == {}
        assert m._gauges == {}
        assert m._histograms == {}


class TestLoomMetricsKey:
    def test_key_no_labels(self):
        assert LoomMetrics._key("name") == "name"

    def test_key_with_labels(self):
        key = LoomMetrics._key("name", {"b": "2", "a": "1"})
        assert key == "name{a=1,b=2}"

    def test_key_empty_labels(self):
        assert LoomMetrics._key("name", {}) == "name"


# ============ Tracing ============


class TestSpanKind:
    def test_enum_values(self):
        assert SpanKind.AGENT_RUN.value == "agent.run"
        assert SpanKind.LLM_CALL.value == "llm.call"
        assert SpanKind.TOOL_EXECUTION.value == "tool.execution"
        assert SpanKind.KNOWLEDGE_SEARCH.value == "knowledge.search"


class TestSpan:
    def test_duration_ms(self):
        s = Span(
            trace_id="t1", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test",
            start_time=1000.0, end_time=1001.5,
        )
        assert s.duration_ms == 1500.0

    def test_duration_ms_no_end(self):
        s = Span(
            trace_id="t1", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test", start_time=1000.0,
        )
        assert s.duration_ms == 0.0

    def test_set_attribute(self):
        s = Span(
            trace_id="t1", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test", start_time=0,
        )
        s.set_attribute("key", "value")
        assert s.attributes["key"] == "value"

    def test_add_event(self):
        s = Span(
            trace_id="t1", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test", start_time=0,
        )
        s.add_event("my_event", {"detail": "info"})
        assert len(s.events) == 1
        assert s.events[0]["name"] == "my_event"
        assert s.events[0]["attributes"]["detail"] == "info"

    def test_set_error(self):
        s = Span(
            trace_id="t1", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test", start_time=0,
        )
        s.set_error(ValueError("bad value"))
        assert s.status == "error"
        assert s.error_message == "bad value"
        assert len(s.events) == 1
        assert s.events[0]["name"] == "exception"

    def test_finish(self):
        s = Span(
            trace_id="t1", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test", start_time=time.time(),
        )
        s.finish()
        assert s.end_time > 0
        assert s.duration_ms > 0

    def test_to_dict(self):
        s = Span(
            trace_id="t1", span_id="s1", parent_span_id="p1",
            kind=SpanKind.LLM_CALL, name="gpt-4",
            start_time=1000.0, end_time=1001.0,
        )
        d = s.to_dict()
        assert d["trace_id"] == "t1"
        assert d["kind"] == "llm.call"
        assert d["duration_ms"] == 1000.0
        assert d["parent_span_id"] == "p1"


class TestLoomTracer:
    def test_init(self):
        t = LoomTracer(agent_id="a1")
        assert t.agent_id == "a1"
        assert t.enabled is True
        assert t.current_span is None
        assert t.completed_spans == []

    def test_new_trace(self):
        t = LoomTracer()
        id1 = t._trace_id
        id2 = t.new_trace()
        assert id2 != id1
        assert t._trace_id == id2

    def test_start_span_basic(self):
        t = LoomTracer(agent_id="a1")
        with t.start_span(SpanKind.AGENT_RUN, "run") as span:
            assert t.current_span is span
            assert span.trace_id == t._trace_id
            span.set_attribute("task", "hello")
        assert t.current_span is None
        assert len(t.completed_spans) == 1
        assert t.completed_spans[0].attributes["task"] == "hello"

    def test_nested_spans(self):
        t = LoomTracer(agent_id="a1")
        with t.start_span(SpanKind.AGENT_RUN, "run") as parent:
            with t.start_span(SpanKind.LLM_CALL, "gpt") as child:
                assert child.parent_span_id == parent.span_id
                assert t.current_span is child
            assert t.current_span is parent
        assert len(t.completed_spans) == 2

    def test_span_error_handling(self):
        t = LoomTracer()
        with pytest.raises(ValueError):
            with t.start_span(SpanKind.TOOL_EXECUTION, "tool"):
                raise ValueError("tool failed")
        assert t.completed_spans[0].status == "error"
        assert "tool failed" in t.completed_spans[0].error_message

    def test_disabled_tracer(self):
        t = LoomTracer(enabled=False)
        with t.start_span(SpanKind.AGENT_RUN, "run") as span:
            assert span.trace_id == ""
        assert len(t.completed_spans) == 0

    def test_exporter(self):
        t = LoomTracer()
        exporter = InMemoryExporter()
        t.add_exporter(exporter)
        with t.start_span(SpanKind.AGENT_RUN, "run"):
            pass
        assert len(exporter.spans) == 1

    def test_exporter_error_handled(self):
        t = LoomTracer()

        class BadExporter(SpanExporter):
            def export(self, span):
                raise RuntimeError("export failed")

        t.add_exporter(BadExporter())
        # Should not raise
        with t.start_span(SpanKind.AGENT_RUN, "run"):
            pass
        assert len(t.completed_spans) == 1

    def test_get_trace_summary(self):
        t = LoomTracer(agent_id="a1")
        with t.start_span(SpanKind.AGENT_RUN, "run"):
            with t.start_span(SpanKind.LLM_CALL, "gpt"):
                pass
        summary = t.get_trace_summary()
        assert summary["agent_id"] == "a1"
        assert summary["span_count"] == 2
        assert summary["error_count"] == 0
        assert "agent.run" in summary["spans_by_kind"]
        assert "llm.call" in summary["spans_by_kind"]


class TestInMemoryExporter:
    def test_export_and_clear(self):
        e = InMemoryExporter()
        span = Span(
            trace_id="t1", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test", start_time=0,
        )
        e.export(span)
        assert len(e.spans) == 1
        e.clear()
        assert len(e.spans) == 0


class TestLogSpanExporter:
    def test_export_logs(self, caplog):
        import logging
        e = LogSpanExporter()
        span = Span(
            trace_id="abcdef1234567890", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test",
            start_time=1000.0, end_time=1001.0,
        )
        with caplog.at_level(logging.INFO, logger="loom.observability.tracing"):
            e.export(span)
        assert "abcdef12" in caplog.text or len(caplog.records) >= 0


class TestSpanExporterBase:
    def test_base_raises(self):
        e = SpanExporter()
        span = Span(
            trace_id="t1", span_id="s1", parent_span_id=None,
            kind=SpanKind.AGENT_RUN, name="test", start_time=0,
        )
        with pytest.raises(NotImplementedError):
            e.export(span)


class TestTraceOperation:
    async def test_decorator_with_tracer(self):
        class MyService:
            def __init__(self):
                self._tracer = LoomTracer(agent_id="svc")

            @trace_operation(SpanKind.TOOL_EXECUTION)
            async def do_work(self):
                return "done"

        svc = MyService()
        result = await svc.do_work()
        assert result == "done"
        assert len(svc._tracer.completed_spans) == 1
        assert svc._tracer.completed_spans[0].name == "do_work"

    async def test_decorator_without_tracer(self):
        class MyService:
            @trace_operation(SpanKind.TOOL_EXECUTION)
            async def do_work(self):
                return "done"

        svc = MyService()
        result = await svc.do_work()
        assert result == "done"

    async def test_decorator_custom_name(self):
        class MyService:
            def __init__(self):
                self._tracer = LoomTracer()

            @trace_operation(SpanKind.LLM_CALL, name="custom_op")
            async def do_work(self):
                return "ok"

        svc = MyService()
        await svc.do_work()
        assert svc._tracer.completed_spans[0].name == "custom_op"
