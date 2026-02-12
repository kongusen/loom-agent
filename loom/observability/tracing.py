"""
Tracing - 结构化追踪

为 Agent 执行链路提供端到端追踪能力。
支持 OpenTelemetry 协议，无 OTEL 时降级到 structlog。
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SpanKind(Enum):
    """Span 类型"""

    AGENT_RUN = "agent.run"
    AGENT_ITERATION = "agent.iteration"
    LLM_CALL = "llm.call"
    TOOL_EXECUTION = "tool.execution"
    MEMORY_READ = "memory.read"
    MEMORY_WRITE = "memory.write"
    CONTEXT_BUILD = "context.build"
    DELEGATION = "agent.delegation"
    PLANNING = "agent.planning"
    SKILL_ACTIVATION = "skill.activation"
    KNOWLEDGE_SEARCH = "knowledge.search"  # 主动搜索（query 工具）
    KNOWLEDGE_RETRIEVAL = "knowledge.retrieval"  # 被动检索（context building）


@dataclass
class Span:
    """追踪 Span — 记录单个操作的生命周期"""

    trace_id: str
    span_id: str
    parent_span_id: str | None
    kind: SpanKind
    name: str
    start_time: float
    end_time: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok | error
    error_message: str = ""

    @property
    def duration_ms(self) -> float:
        if self.end_time <= 0:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def set_error(self, error: Exception) -> None:
        self.status = "error"
        self.error_message = str(error)
        self.add_event(
            "exception",
            {
                "type": type(error).__name__,
                "message": str(error),
            },
        )

    def finish(self) -> None:
        self.end_time = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind.value,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
            "error_message": self.error_message,
        }


class LoomTracer:
    """
    Loom 追踪器

    管理 trace 和 span 的生命周期。
    支持嵌套 span（Agent → Iteration → LLM Call → Tool）。

    用法：
        tracer = LoomTracer(agent_id="agent-1")
        with tracer.start_span(SpanKind.AGENT_RUN, "run") as span:
            span.set_attribute("task", "hello")
            with tracer.start_span(SpanKind.LLM_CALL, "gpt-4o") as child:
                child.set_attribute("tokens_in", 100)
    """

    def __init__(self, agent_id: str = "", enabled: bool = True):
        self.agent_id = agent_id
        self.enabled = enabled
        self._trace_id: str = uuid4().hex[:16]
        self._spans: list[Span] = []
        self._active_span: Span | None = None
        self._exporters: list[SpanExporter] = []

    def new_trace(self) -> str:
        """开始新的 trace"""
        self._trace_id = uuid4().hex[:16]
        self._spans = []
        self._active_span = None
        return self._trace_id

    @contextmanager
    def start_span(
        self,
        kind: SpanKind,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        """创建并管理一个 Span 的生命周期"""
        if not self.enabled:
            # 返回一个 no-op span
            yield Span(
                trace_id="",
                span_id="",
                parent_span_id=None,
                kind=kind,
                name=name,
                start_time=0,
            )
            return

        parent_id = self._active_span.span_id if self._active_span else None
        span = Span(
            trace_id=self._trace_id,
            span_id=uuid4().hex[:12],
            parent_span_id=parent_id,
            kind=kind,
            name=name,
            start_time=time.time(),
            attributes={"agent_id": self.agent_id, **(attributes or {})},
        )

        previous_active = self._active_span
        self._active_span = span

        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            span.finish()
            self._spans.append(span)
            self._active_span = previous_active
            self._export_span(span)

    @property
    def current_span(self) -> Span | None:
        return self._active_span

    @property
    def completed_spans(self) -> list[Span]:
        return list(self._spans)

    def add_exporter(self, exporter: SpanExporter) -> None:
        self._exporters.append(exporter)

    def _export_span(self, span: Span) -> None:
        for exporter in self._exporters:
            try:
                exporter.export(span)
            except Exception:
                logger.warning("Failed to export span %s", span.span_id)

    def get_trace_summary(self) -> dict[str, Any]:
        """获取当前 trace 的摘要"""
        total_duration = sum(s.duration_ms for s in self._spans)
        error_count = sum(1 for s in self._spans if s.status == "error")
        by_kind: dict[str, int] = {}
        for s in self._spans:
            by_kind[s.kind.value] = by_kind.get(s.kind.value, 0) + 1

        return {
            "trace_id": self._trace_id,
            "agent_id": self.agent_id,
            "span_count": len(self._spans),
            "total_duration_ms": round(total_duration, 2),
            "error_count": error_count,
            "spans_by_kind": by_kind,
        }


class SpanExporter:
    """Span 导出器基类"""

    def export(self, span: Span) -> None:
        raise NotImplementedError


class LogSpanExporter(SpanExporter):
    """将 Span 输出到日志"""

    def export(self, span: Span) -> None:
        status = "ERR" if span.status == "error" else "OK"
        logger.info(
            "[%s] %s %s (%.1fms) %s",
            span.trace_id[:8],
            span.kind.value,
            span.name,
            span.duration_ms,
            status,
        )


class InMemoryExporter(SpanExporter):
    """内存导出器（用于测试和调试）"""

    def __init__(self) -> None:
        self.spans: list[Span] = []

    def export(self, span: Span) -> None:
        self.spans.append(span)

    def clear(self) -> None:
        self.spans.clear()


def trace_operation(kind: SpanKind, name: str | None = None):
    """
    装饰器：自动追踪异步函数

    用法：
        @trace_operation(SpanKind.TOOL_EXECUTION)
        async def execute_tool(self, tool_name, args):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            tracer: LoomTracer | None = getattr(self, "_tracer", None)
            op_name = name or func.__name__
            if tracer is None:
                return await func(self, *args, **kwargs)
            with tracer.start_span(kind, op_name):
                result = await func(self, *args, **kwargs)
                return result

        return wrapper

    return decorator
