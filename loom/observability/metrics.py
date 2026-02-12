"""
Metrics - 指标收集

为 Agent 运行时提供关键指标的采集和暴露。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricPoint:
    """单个指标数据点"""

    name: str
    value: float
    metric_type: MetricType
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class LoomMetrics:
    """
    Loom 指标收集器

    预定义 Agent 运行时关键指标，支持 counter / gauge / histogram。

    用法：
        metrics = LoomMetrics(agent_id="agent-1")
        metrics.increment("iterations_total")
        metrics.record_tokens(input_tokens=500, output_tokens=200)
        metrics.observe_latency("llm_call", 1.23)
        print(metrics.snapshot())
    """

    # 预定义指标名
    ITERATIONS_TOTAL = "agent_iterations_total"
    TOKEN_INPUT = "agent_token_input"
    TOKEN_OUTPUT = "agent_token_output"
    TOOL_CALLS_TOTAL = "agent_tool_calls_total"
    TOOL_ERRORS_TOTAL = "agent_tool_errors_total"
    LLM_LATENCY = "agent_llm_latency_ms"
    CONTEXT_BUDGET_USED = "agent_context_budget_used_ratio"
    MEMORY_L1_USAGE = "memory_l1_usage_ratio"
    MEMORY_L2_USAGE = "memory_l2_usage_ratio"
    DELEGATION_TOTAL = "agent_delegation_total"
    KNOWLEDGE_SEARCH_TOTAL = "knowledge_search_total"
    KNOWLEDGE_SEARCH_LATENCY = "knowledge_search_latency_ms"
    KNOWLEDGE_HIT_RATE = "knowledge_hit_rate"
    KNOWLEDGE_RESULTS_COUNT = "knowledge_results_count"

    def __init__(self, agent_id: str = "", enabled: bool = True):
        self.agent_id = agent_id
        self.enabled = enabled
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        if not self.enabled:
            return
        key = self._key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        if not self.enabled:
            return
        self._gauges[self._key(name, labels)] = value

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        if not self.enabled:
            return
        key = self._key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def record_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.increment(self.TOKEN_INPUT, input_tokens)
        self.increment(self.TOKEN_OUTPUT, output_tokens)

    def observe_latency(self, operation: str, duration_ms: float) -> None:
        self.observe(f"{operation}_latency_ms", duration_ms)

    def snapshot(self) -> dict[str, Any]:
        """导出当前所有指标的快照"""
        result: dict[str, Any] = {"agent_id": self.agent_id}

        result["counters"] = dict(self._counters)
        result["gauges"] = dict(self._gauges)

        histograms: dict[str, dict[str, float]] = {}
        for key, values in self._histograms.items():
            if values:
                sorted_v = sorted(values)
                histograms[key] = {
                    "count": len(values),
                    "sum": sum(values),
                    "min": sorted_v[0],
                    "max": sorted_v[-1],
                    "avg": sum(values) / len(values),
                    "p50": sorted_v[len(sorted_v) // 2],
                    "p95": sorted_v[int(len(sorted_v) * 0.95)],
                    "p99": sorted_v[int(len(sorted_v) * 0.99)],
                }
        result["histograms"] = histograms
        return result

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()

    @staticmethod
    def _key(name: str, labels: dict[str, str] | None = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
