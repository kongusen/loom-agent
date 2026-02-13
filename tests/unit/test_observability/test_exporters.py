"""
Tests for loom/observability/exporters.py - OTLP + Console exporters
"""

import io
import json
from unittest.mock import MagicMock, patch

from loom.observability.exporters import (
    ConsoleSpanExporter,
    OTLPMetricsExporter,
    OTLPSpanExporter,
    _to_otlp_value,
)
from loom.observability.tracing import Span

# ==================== _to_otlp_value ====================


class TestToOtlpValue:
    def test_bool(self):
        assert _to_otlp_value(True) == {"boolValue": True}
        assert _to_otlp_value(False) == {"boolValue": False}

    def test_int(self):
        assert _to_otlp_value(42) == {"intValue": "42"}

    def test_float(self):
        assert _to_otlp_value(3.14) == {"doubleValue": 3.14}

    def test_string(self):
        assert _to_otlp_value("hello") == {"stringValue": "hello"}

    def test_none_becomes_string(self):
        assert _to_otlp_value(None) == {"stringValue": "None"}

    def test_bool_before_int(self):
        # bool is subclass of int, must check bool first
        result = _to_otlp_value(True)
        assert "boolValue" in result


# ==================== OTLPSpanExporter ====================


class TestOTLPSpanExporter:
    def _make_span(self, **overrides) -> Span:
        defaults = {
            "trace_id": "abc123",
            "span_id": "def456",
            "name": "test-span",
            "start_time": 1000.0,
            "end_time": 1001.0,
            "attributes": {"key": "value"},
            "status": "ok",
            "error_message": "",
            "parent_span_id": "",
            "events": [],
        }
        defaults.update(overrides)
        span = MagicMock(spec=Span)
        for k, v in defaults.items():
            setattr(span, k, v)
        return span

    def test_init_defaults(self):
        exp = OTLPSpanExporter()
        assert exp._endpoint == "http://localhost:4318/v1/traces"
        assert exp._service_name == "loom-agent"
        assert exp._timeout == 5.0

    def test_init_custom(self):
        exp = OTLPSpanExporter(
            endpoint="http://custom:4318/v1/traces",
            headers={"Authorization": "Bearer x"},
            service_name="my-svc",
            timeout=10.0,
        )
        assert exp._endpoint == "http://custom:4318/v1/traces"
        assert exp._headers == {"Authorization": "Bearer x"}
        assert exp._service_name == "my-svc"

    def test_to_otlp_basic(self):
        exp = OTLPSpanExporter()
        span = self._make_span()
        payload = exp._to_otlp(span)

        assert "resourceSpans" in payload
        rs = payload["resourceSpans"][0]
        assert rs["resource"]["attributes"][0]["value"]["stringValue"] == "loom-agent"

        otlp_span = rs["scopeSpans"][0]["spans"][0]
        assert otlp_span["name"] == "test-span"
        assert otlp_span["kind"] == 1
        assert otlp_span["status"]["code"] == 1  # OK

    def test_to_otlp_error_status(self):
        exp = OTLPSpanExporter()
        span = self._make_span(status="error", error_message="boom")
        payload = exp._to_otlp(span)
        otlp_span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert otlp_span["status"]["code"] == 2

    def test_to_otlp_with_parent(self):
        exp = OTLPSpanExporter()
        span = self._make_span(parent_span_id="parent123")
        payload = exp._to_otlp(span)
        otlp_span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert "parentSpanId" in otlp_span

    def test_to_otlp_with_events(self):
        exp = OTLPSpanExporter()
        span = self._make_span(
            events=[
                {"timestamp": 1000.5, "name": "evt1", "attributes": {"a": 1}},
            ]
        )
        payload = exp._to_otlp(span)
        otlp_span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert len(otlp_span["events"]) == 1
        assert otlp_span["events"][0]["name"] == "evt1"

    def test_to_otlp_zero_end_time(self):
        exp = OTLPSpanExporter()
        span = self._make_span(end_time=0)
        payload = exp._to_otlp(span)
        otlp_span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert otlp_span["endTimeUnixNano"] == "0"

    @patch("loom.observability.exporters.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        exp = OTLPSpanExporter()
        exp._send({"test": "data"})
        mock_urlopen.assert_called_once()

    @patch("loom.observability.exporters.urllib.request.urlopen", side_effect=Exception("fail"))
    def test_send_failure_silent(self, mock_urlopen):
        exp = OTLPSpanExporter()
        # Should not raise
        exp._send({"test": "data"})

    @patch("loom.observability.exporters.urllib.request.urlopen")
    def test_export_calls_send(self, mock_urlopen):
        exp = OTLPSpanExporter()
        span = self._make_span()
        exp.export(span)
        mock_urlopen.assert_called_once()


# ==================== OTLPMetricsExporter ====================


class TestOTLPMetricsExporter:
    def test_init_defaults(self):
        exp = OTLPMetricsExporter()
        assert exp._endpoint == "http://localhost:4318/v1/metrics"

    def test_to_otlp_counters(self):
        exp = OTLPMetricsExporter()
        snapshot = {"counters": {"requests": 100}, "gauges": {}, "histograms": {}}
        payload = exp._to_otlp(snapshot)
        metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
        assert len(metrics) == 1
        assert metrics[0]["name"] == "requests"
        assert metrics[0]["sum"]["dataPoints"][0]["asDouble"] == 100

    def test_to_otlp_gauges(self):
        exp = OTLPMetricsExporter()
        snapshot = {"counters": {}, "gauges": {"memory_mb": 256.5}, "histograms": {}}
        payload = exp._to_otlp(snapshot)
        metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
        assert metrics[0]["name"] == "memory_mb"
        assert metrics[0]["gauge"]["dataPoints"][0]["asDouble"] == 256.5

    def test_to_otlp_histograms(self):
        exp = OTLPMetricsExporter()
        snapshot = {
            "counters": {},
            "gauges": {},
            "histograms": {
                "latency": {"count": 50, "sum": 100.0, "p50": 1.5, "p95": 3.0, "p99": 5.0}
            },
        }
        payload = exp._to_otlp(snapshot)
        metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
        assert metrics[0]["name"] == "latency"
        dp = metrics[0]["summary"]["dataPoints"][0]
        assert dp["count"] == "50"
        assert len(dp["quantileValues"]) == 3

    def test_to_otlp_empty_snapshot(self):
        exp = OTLPMetricsExporter()
        payload = exp._to_otlp({"counters": {}, "gauges": {}, "histograms": {}})
        metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
        assert metrics == []

    @patch("loom.observability.exporters.urllib.request.urlopen")
    def test_export(self, mock_urlopen):
        exp = OTLPMetricsExporter()
        exp.export({"counters": {"x": 1}, "gauges": {}, "histograms": {}})
        mock_urlopen.assert_called_once()

    @patch("loom.observability.exporters.urllib.request.urlopen", side_effect=Exception("fail"))
    def test_export_failure_silent(self, mock_urlopen):
        exp = OTLPMetricsExporter()
        exp.export({"counters": {}, "gauges": {}, "histograms": {}})


# ==================== ConsoleSpanExporter ====================


class TestConsoleSpanExporter:
    def test_export_to_stream(self):
        stream = io.StringIO()
        exp = ConsoleSpanExporter(stream=stream)
        span = MagicMock()
        span.to_dict.return_value = {"name": "test", "trace_id": "abc"}
        exp.export(span)
        output = stream.getvalue()
        data = json.loads(output.strip())
        assert data["name"] == "test"

    def test_export_pretty(self):
        stream = io.StringIO()
        exp = ConsoleSpanExporter(stream=stream, pretty=True)
        span = MagicMock()
        span.to_dict.return_value = {"name": "test"}
        exp.export(span)
        output = stream.getvalue()
        # Pretty print has newlines within the JSON
        assert "\n" in output.strip()

    def test_export_not_pretty(self):
        stream = io.StringIO()
        exp = ConsoleSpanExporter(stream=stream, pretty=False)
        span = MagicMock()
        span.to_dict.return_value = {"name": "test"}
        exp.export(span)
        output = stream.getvalue().strip()
        # Single line JSON
        assert "\n" not in output
