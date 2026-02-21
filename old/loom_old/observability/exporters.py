"""
OTEL Exporters - OpenTelemetry 协议导出器

通过 OTLP/HTTP 协议导出 Span 和 Metrics，无需 opentelemetry-sdk 依赖。
失败时静默降级到日志。
"""

from __future__ import annotations

import json
import logging
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from loom.observability.tracing import Span, SpanExporter

logger = logging.getLogger(__name__)


class OTLPSpanExporter(SpanExporter):
    """
    通过 OTLP/HTTP 导出 Span 到 Jaeger / Tempo / OTEL Collector

    用法：
        exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
        tracer.add_exporter(exporter)
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:4318/v1/traces",
        headers: dict[str, str] | None = None,
        service_name: str = "loom-agent",
        timeout: float = 5.0,
    ):
        self._endpoint = endpoint
        self._headers = headers or {}
        self._service_name = service_name
        self._timeout = timeout

    def export(self, span: Span) -> None:
        payload = self._to_otlp(span)
        self._send(payload)

    def _to_otlp(self, span: Span) -> dict[str, Any]:
        """Loom Span → OTLP ResourceSpans JSON"""
        otlp_span: dict[str, Any] = {
            "traceId": span.trace_id.ljust(32, "0"),
            "spanId": span.span_id.ljust(16, "0"),
            "name": span.name,
            "kind": 1,  # SPAN_KIND_INTERNAL
            "startTimeUnixNano": str(int(span.start_time * 1e9)),
            "endTimeUnixNano": str(int(span.end_time * 1e9)) if span.end_time > 0 else "0",
            "attributes": [
                {"key": k, "value": _to_otlp_value(v)} for k, v in span.attributes.items()
            ],
            "status": {
                "code": 2 if span.status == "error" else 1,  # ERROR=2, OK=1
                "message": span.error_message,
            },
        }
        if span.parent_span_id:
            otlp_span["parentSpanId"] = span.parent_span_id.ljust(16, "0")

        if span.events:
            otlp_span["events"] = [
                {
                    "timeUnixNano": str(int(e.get("timestamp", 0) * 1e9)),
                    "name": e.get("name", ""),
                    "attributes": [
                        {"key": k, "value": _to_otlp_value(v)}
                        for k, v in e.get("attributes", {}).items()
                    ],
                }
                for e in span.events
            ]

        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self._service_name}},
                        ],
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "loom.observability"},
                            "spans": [otlp_span],
                        }
                    ],
                }
            ],
        }

    def _send(self, payload: dict[str, Any]) -> None:
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    **self._headers,
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=self._timeout)
        except Exception:
            logger.debug("OTLP span export failed", exc_info=True)


class OTLPMetricsExporter:
    """
    通过 OTLP/HTTP 导出 Metrics 快照

    用法：
        exporter = OTLPMetricsExporter()
        exporter.export(metrics.snapshot())
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:4318/v1/metrics",
        headers: dict[str, str] | None = None,
        service_name: str = "loom-agent",
        timeout: float = 5.0,
    ):
        self._endpoint = endpoint
        self._headers = headers or {}
        self._service_name = service_name
        self._timeout = timeout

    def export(self, snapshot: dict[str, Any]) -> None:
        payload = self._to_otlp(snapshot)
        self._send(payload)

    def _to_otlp(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """LoomMetrics.snapshot() → OTLP Metrics JSON"""
        now_ns = str(int(time.time() * 1e9))
        metrics: list[dict[str, Any]] = []

        # Counters → Sum
        for name, value in snapshot.get("counters", {}).items():
            metrics.append(
                {
                    "name": name,
                    "sum": {
                        "dataPoints": [
                            {
                                "asDouble": value,
                                "timeUnixNano": now_ns,
                                "isMonotonic": True,
                                "aggregationTemporality": 2,  # CUMULATIVE
                            }
                        ],
                    },
                }
            )

        # Gauges → Gauge
        for name, value in snapshot.get("gauges", {}).items():
            metrics.append(
                {
                    "name": name,
                    "gauge": {
                        "dataPoints": [
                            {
                                "asDouble": value,
                                "timeUnixNano": now_ns,
                            }
                        ],
                    },
                }
            )

        # Histograms → Summary (simplified)
        for name, stats in snapshot.get("histograms", {}).items():
            metrics.append(
                {
                    "name": name,
                    "summary": {
                        "dataPoints": [
                            {
                                "timeUnixNano": now_ns,
                                "count": str(int(stats.get("count", 0))),
                                "sum": stats.get("sum", 0),
                                "quantileValues": [
                                    {"quantile": 0.5, "value": stats.get("p50", 0)},
                                    {"quantile": 0.95, "value": stats.get("p95", 0)},
                                    {"quantile": 0.99, "value": stats.get("p99", 0)},
                                ],
                            }
                        ],
                    },
                }
            )

        return {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self._service_name}},
                        ],
                    },
                    "scopeMetrics": [
                        {
                            "scope": {"name": "loom.observability"},
                            "metrics": metrics,
                        }
                    ],
                }
            ],
        }

    def _send(self, payload: dict[str, Any]) -> None:
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    **self._headers,
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=self._timeout)
        except Exception:
            logger.debug("OTLP metrics export failed", exc_info=True)


class ConsoleSpanExporter(SpanExporter):
    """
    结构化 JSON 输出到 stderr（开发调试用）

    用法：
        tracer.add_exporter(ConsoleSpanExporter())
    """

    def __init__(self, stream: Any = None, pretty: bool = False):
        self._stream = stream or sys.stderr
        self._pretty = pretty

    def export(self, span: Span) -> None:
        data = span.to_dict()
        indent = 2 if self._pretty else None
        line = json.dumps(data, ensure_ascii=False, default=str, indent=indent)
        self._stream.write(line + "\n")
        self._stream.flush()


def _to_otlp_value(value: Any) -> dict[str, Any]:
    """Python 值 → OTLP AnyValue"""
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}
