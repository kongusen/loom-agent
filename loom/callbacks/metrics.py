from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PerformanceMetrics:
    total_iterations: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    total_errors: int = 0
    extras: Dict[str, float] = field(default_factory=dict)


class MetricsCollector:
    def __init__(self) -> None:
        self.metrics = PerformanceMetrics()

    def summary(self) -> Dict:
        return {
            "iterations": self.metrics.total_iterations,
            "llm_calls": self.metrics.llm_calls,
            "tool_calls": self.metrics.tool_calls,
            "errors": self.metrics.total_errors,
        }

