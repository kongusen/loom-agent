"""
Loom Observability - 可观测性模块

提供结构化追踪 (Tracing)、指标 (Metrics)、事件记录，
支持 OpenTelemetry 协议导出。

设计原则：
- 零侵入：通过装饰器和上下文管理器注入
- 可选依赖：不强制安装 opentelemetry
- 降级优雅：无 OTEL 时回退到 structlog
"""

from loom.observability.exporters import (
    ConsoleSpanExporter,
    OTLPMetricsExporter,
    OTLPSpanExporter,
)
from loom.observability.metrics import LoomMetrics, MetricType
from loom.observability.tracing import LoomTracer, SpanExporter, SpanKind, trace_operation


def setup_otlp(
    endpoint: str = "http://localhost:4318",
    headers: dict[str, str] | None = None,
    service_name: str = "loom-agent",
) -> tuple[OTLPSpanExporter, OTLPMetricsExporter]:
    """
    便捷工厂：创建 OTLP Span + Metrics 导出器对

    用法：
        span_exporter, metrics_exporter = setup_otlp("http://otel-collector:4318")
        agent = Agent.create(..., observability_exporters=[span_exporter])
    """
    span_exp = OTLPSpanExporter(
        endpoint=f"{endpoint.rstrip('/')}/v1/traces",
        headers=headers,
        service_name=service_name,
    )
    metrics_exp = OTLPMetricsExporter(
        endpoint=f"{endpoint.rstrip('/')}/v1/metrics",
        headers=headers,
        service_name=service_name,
    )
    return span_exp, metrics_exp


__all__ = [
    "LoomTracer",
    "LoomMetrics",
    "SpanKind",
    "SpanExporter",
    "MetricType",
    "trace_operation",
    "OTLPSpanExporter",
    "OTLPMetricsExporter",
    "ConsoleSpanExporter",
    "setup_otlp",
]
