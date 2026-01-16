"""
Performance Metrics and Monitoring for LoomMemory System
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class MemoryMetrics:
    """Memory system performance metrics"""

    # Query Performance
    total_queries: int = 0
    avg_query_time_ms: float = 0.0
    l1_queries: int = 0
    l2_queries: int = 0
    l3_queries: int = 0
    l4_queries: int = 0

    # Vector Search Performance
    vector_searches: int = 0
    avg_vector_search_time_ms: float = 0.0
    vector_cache_hits: int = 0
    vector_cache_misses: int = 0

    # Memory Operations
    total_adds: int = 0
    l1_evictions: int = 0
    l4_promotions: int = 0
    compressions_performed: int = 0

    # Storage Stats
    current_l1_size: int = 0
    current_l2_size: int = 0
    current_l3_size: int = 0
    current_l4_size: int = 0
    total_memory_units: int = 0


@dataclass
class RoutingMetrics:
    """System 1/2 routing performance metrics"""

    # Routing Decisions
    total_decisions: int = 0
    system1_routed: int = 0
    system2_routed: int = 0
    adaptive_routed: int = 0

    # System 1 Performance
    s1_calls: int = 0
    s1_successes: int = 0
    s1_failures: int = 0
    s1_avg_confidence: float = 0.0
    s1_avg_time_ms: float = 0.0
    s1_avg_tokens: float = 0.0

    # System 2 Performance
    s2_calls: int = 0
    s2_avg_time_ms: float = 0.0
    s2_avg_tokens: float = 0.0
    s2_avg_iterations: float = 0.0

    # Adaptive Fallback
    s1_to_s2_switches: int = 0
    switch_rate: float = 0.0

    # Cost Savings
    total_tokens_saved: int = 0
    estimated_cost_saved_usd: float = 0.0


@dataclass
class ContextMetrics:
    """Context assembly performance metrics"""

    # Assembly Performance
    total_assemblies: int = 0
    avg_assembly_time_ms: float = 0.0

    # Token Usage
    avg_context_tokens: float = 0.0
    max_context_tokens: int = 0
    min_context_tokens: int = 0

    # Curation Stats
    avg_units_curated: float = 0.0
    avg_units_selected: float = 0.0
    selection_ratio: float = 0.0

    # Snippet Usage
    snippets_created: int = 0
    snippets_loaded: int = 0
    snippet_load_rate: float = 0.0


class MetricsCollector:
    """
    Centralized metrics collection for the entire LoomMemory system.
    """

    def __init__(self):
        self.memory_metrics = MemoryMetrics()
        self.routing_metrics = RoutingMetrics()
        self.context_metrics = ContextMetrics()

        # Timing helpers
        self._query_times: list[float] = []
        self._vector_search_times: list[float] = []
        self._assembly_times: list[float] = []
        self._s1_times: list[float] = []
        self._s2_times: list[float] = []

        # Confidence tracking
        self._s1_confidences: list[float] = []

        # Token tracking
        self._s1_tokens: list[int] = []
        self._s2_tokens: list[int] = []
        self._context_tokens: list[int] = []

    def record_query(self, tier: str, duration_ms: float):
        """Record a memory query."""
        self.memory_metrics.total_queries += 1
        self._query_times.append(duration_ms)
        self.memory_metrics.avg_query_time_ms = sum(self._query_times) / len(self._query_times)

        # Track by tier
        if tier == "L1":
            self.memory_metrics.l1_queries += 1
        elif tier == "L2":
            self.memory_metrics.l2_queries += 1
        elif tier == "L3":
            self.memory_metrics.l3_queries += 1
        elif tier == "L4":
            self.memory_metrics.l4_queries += 1

    def record_vector_search(self, duration_ms: float, cache_hit: bool = False):
        """Record a vector search operation."""
        self.memory_metrics.vector_searches += 1
        self._vector_search_times.append(duration_ms)
        self.memory_metrics.avg_vector_search_time_ms = sum(self._vector_search_times) / len(
            self._vector_search_times
        )

        if cache_hit:
            self.memory_metrics.vector_cache_hits += 1
        else:
            self.memory_metrics.vector_cache_misses += 1

    def record_memory_add(self, _tier: str):
        """Record a memory unit addition."""
        self.memory_metrics.total_adds += 1

    def record_l1_eviction(self):
        """Record an L1 eviction."""
        self.memory_metrics.l1_evictions += 1

    def record_l4_promotion(self):
        """Record a promotion to L4."""
        self.memory_metrics.l4_promotions += 1

    def record_compression(self):
        """Record a memory compression operation."""
        self.memory_metrics.compressions_performed += 1

    def update_memory_sizes(self, l1: int, l2: int, l3: int, l4: int):
        """Update current memory sizes."""
        self.memory_metrics.current_l1_size = l1
        self.memory_metrics.current_l2_size = l2
        self.memory_metrics.current_l3_size = l3
        self.memory_metrics.current_l4_size = l4
        self.memory_metrics.total_memory_units = l1 + l2 + l3 + l4

    def record_routing_decision(self, system: str):
        """Record a routing decision."""
        self.routing_metrics.total_decisions += 1

        if system == "system_1":
            self.routing_metrics.system1_routed += 1
        elif system == "system_2":
            self.routing_metrics.system2_routed += 1
        elif system == "adaptive":
            self.routing_metrics.adaptive_routed += 1

    def record_s1_execution(
        self, duration_ms: float, tokens: int, confidence: float, success: bool
    ):
        """Record a System 1 execution."""
        self.routing_metrics.s1_calls += 1
        self._s1_times.append(duration_ms)
        self._s1_tokens.append(tokens)
        self._s1_confidences.append(confidence)

        if success:
            self.routing_metrics.s1_successes += 1
        else:
            self.routing_metrics.s1_failures += 1

        # Update averages
        self.routing_metrics.s1_avg_time_ms = sum(self._s1_times) / len(self._s1_times)
        self.routing_metrics.s1_avg_tokens = sum(self._s1_tokens) / len(self._s1_tokens)
        self.routing_metrics.s1_avg_confidence = sum(self._s1_confidences) / len(
            self._s1_confidences
        )

    def record_s2_execution(self, duration_ms: float, tokens: int, _iterations: int):
        """Record a System 2 execution."""
        self.routing_metrics.s2_calls += 1
        self._s2_times.append(duration_ms)
        self._s2_tokens.append(tokens)

        # Update averages
        self.routing_metrics.s2_avg_time_ms = sum(self._s2_times) / len(self._s2_times)
        self.routing_metrics.s2_avg_tokens = sum(self._s2_tokens) / len(self._s2_tokens)

    def record_s1_to_s2_switch(self):
        """Record a fallback from S1 to S2."""
        self.routing_metrics.s1_to_s2_switches += 1

        # Update switch rate
        if self.routing_metrics.s1_calls > 0:
            self.routing_metrics.switch_rate = (
                self.routing_metrics.s1_to_s2_switches / self.routing_metrics.s1_calls
            )

    def record_token_savings(self, tokens_saved: int, cost_per_1k_tokens: float = 0.002):
        """Record token savings from using System 1."""
        self.routing_metrics.total_tokens_saved += tokens_saved
        self.routing_metrics.estimated_cost_saved_usd = (
            self.routing_metrics.total_tokens_saved / 1000 * cost_per_1k_tokens
        )

    def record_context_assembly(
        self, duration_ms: float, tokens: int, units_curated: int, units_selected: int
    ):
        """Record a context assembly operation."""
        self.context_metrics.total_assemblies += 1
        self._assembly_times.append(duration_ms)
        self._context_tokens.append(tokens)

        # Update averages
        self.context_metrics.avg_assembly_time_ms = sum(self._assembly_times) / len(
            self._assembly_times
        )
        self.context_metrics.avg_context_tokens = sum(self._context_tokens) / len(
            self._context_tokens
        )

        # Update min/max
        if tokens > self.context_metrics.max_context_tokens:
            self.context_metrics.max_context_tokens = tokens
        if (
            self.context_metrics.min_context_tokens == 0
            or tokens < self.context_metrics.min_context_tokens
        ):
            self.context_metrics.min_context_tokens = tokens

        # Update curation stats
        total_curated = self.context_metrics.avg_units_curated * (
            self.context_metrics.total_assemblies - 1
        )
        self.context_metrics.avg_units_curated = (
            total_curated + units_curated
        ) / self.context_metrics.total_assemblies

        total_selected = self.context_metrics.avg_units_selected * (
            self.context_metrics.total_assemblies - 1
        )
        self.context_metrics.avg_units_selected = (
            total_selected + units_selected
        ) / self.context_metrics.total_assemblies

        if units_curated > 0:
            self.context_metrics.selection_ratio = units_selected / units_curated

    def record_snippet_created(self):
        """Record a snippet creation."""
        self.context_metrics.snippets_created += 1

    def record_snippet_loaded(self):
        """Record a snippet load."""
        self.context_metrics.snippets_loaded += 1

        if self.context_metrics.snippets_created > 0:
            self.context_metrics.snippet_load_rate = (
                self.context_metrics.snippets_loaded / self.context_metrics.snippets_created
            )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics."""
        return {
            "memory": asdict(self.memory_metrics),
            "routing": asdict(self.routing_metrics),
            "context": asdict(self.context_metrics),
            "timestamp": datetime.now().isoformat(),
        }

    def reset(self):
        """Reset all metrics."""
        self.memory_metrics = MemoryMetrics()
        self.routing_metrics = RoutingMetrics()
        self.context_metrics = ContextMetrics()
        self._query_times.clear()
        self._vector_search_times.clear()
        self._assembly_times.clear()
        self._s1_times.clear()
        self._s2_times.clear()
        self._s1_confidences.clear()
        self._s1_tokens.clear()
        self._s2_tokens.clear()
        self._context_tokens.clear()
