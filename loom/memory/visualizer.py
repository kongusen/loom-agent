"""
Visualization and Reporting for LoomMemory Metrics
"""
from typing import Dict, Any, Optional
from .metrics import MetricsCollector, MemoryMetrics, RoutingMetrics, ContextMetrics


class MetricsVisualizer:
    """
    Generates human-readable visualizations of metrics.
    """

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def render_memory_status(self) -> str:
        """Render memory tier status as ASCII art."""
        m = self.collector.memory_metrics

        viz = """
╔═══════════════════════════════════════════════════════════╗
║                  LOOM MEMORY STATUS                       ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  L4 Global Knowledge                                      ║
║  ├─ Size: {l4_size:>4} units                                    ║
║  ├─ Promotions: {l4_promo:>4}                                   ║
║  └─ Vector Searches: {vec_search:>4}                            ║
║                                                           ║
║  ─────────────────────────────────────────────────────    ║
║                                                           ║
║  L3 Session History                                       ║
║  ├─ Size: {l3_size:>4} units                                    ║
║  └─ Compressions: {compress:>4}                                 ║
║                                                           ║
║  ─────────────────────────────────────────────────────    ║
║                                                           ║
║  L2 Working Memory                                        ║
║  └─ Size: {l2_size:>4} units                                    ║
║                                                           ║
║  ─────────────────────────────────────────────────────    ║
║                                                           ║
║  L1 Raw IO Buffer                                         ║
║  ├─ Size: {l1_size:>4} units                                    ║
║  └─ Evictions: {l1_evict:>4}                                    ║
║                                                           ║
╠═══════════════════════════════════════════════════════════╣
║  Total Units: {total:>4}  |  Total Queries: {queries:>6}        ║
╚═══════════════════════════════════════════════════════════╝
        """.format(
            l4_size=m.current_l4_size,
            l4_promo=m.l4_promotions,
            vec_search=m.vector_searches,
            l3_size=m.current_l3_size,
            compress=m.compressions_performed,
            l2_size=m.current_l2_size,
            l1_size=m.current_l1_size,
            l1_evict=m.l1_evictions,
            total=m.total_memory_units,
            queries=m.total_queries
        )

        return viz

    def render_routing_performance(self) -> str:
        """Render System 1/2 routing performance."""
        r = self.collector.routing_metrics

        s1_success_rate = (
            (r.s1_successes / r.s1_calls * 100) if r.s1_calls > 0 else 0
        )
        s1_usage_rate = (
            (r.system1_routed / r.total_decisions * 100) if r.total_decisions > 0 else 0
        )

        viz = """
╔═══════════════════════════════════════════════════════════╗
║              SYSTEM 1/2 ROUTING PERFORMANCE               ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Routing Decisions:                                       ║
║  ├─ Total: {total:>6}                                          ║
║  ├─ System 1: {s1:>6} ({s1_pct:>5.1f}%)                            ║
║  ├─ System 2: {s2:>6} ({s2_pct:>5.1f}%)                            ║
║  └─ Adaptive: {adp:>6}                                         ║
║                                                           ║
║  System 1 Performance:                                    ║
║  ├─ Calls: {s1_calls:>6}                                       ║
║  ├─ Success Rate: {s1_success:>5.1f}%                            ║
║  ├─ Avg Confidence: {s1_conf:>5.2f}                             ║
║  ├─ Avg Time: {s1_time:>6.1f}ms                                 ║
║  └─ Avg Tokens: {s1_tok:>6.0f}                                  ║
║                                                           ║
║  System 2 Performance:                                    ║
║  ├─ Calls: {s2_calls:>6}                                       ║
║  ├─ Avg Time: {s2_time:>6.1f}ms                                 ║
║  └─ Avg Tokens: {s2_tok:>6.0f}                                  ║
║                                                           ║
║  Adaptive Fallback:                                       ║
║  ├─ S1→S2 Switches: {switches:>6}                              ║
║  └─ Switch Rate: {switch_rate:>5.1f}%                            ║
║                                                           ║
║  Cost Savings:                                            ║
║  ├─ Tokens Saved: {tokens_saved:>8}                            ║
║  └─ Est. Cost Saved: ${cost_saved:>7.2f}                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """.format(
            total=r.total_decisions,
            s1=r.system1_routed,
            s1_pct=s1_usage_rate,
            s2=r.system2_routed,
            s2_pct=(r.system2_routed / r.total_decisions * 100) if r.total_decisions > 0 else 0,
            adp=r.adaptive_routed,
            s1_calls=r.s1_calls,
            s1_success=s1_success_rate,
            s1_conf=r.s1_avg_confidence,
            s1_time=r.s1_avg_time_ms,
            s1_tok=r.s1_avg_tokens,
            s2_calls=r.s2_calls,
            s2_time=r.s2_avg_time_ms,
            s2_tok=r.s2_avg_tokens,
            switches=r.s1_to_s2_switches,
            switch_rate=r.switch_rate * 100,
            tokens_saved=r.total_tokens_saved,
            cost_saved=r.estimated_cost_saved_usd
        )

        return viz

    def render_context_performance(self) -> str:
        """Render context assembly performance."""
        c = self.collector.context_metrics

        viz = """
╔═══════════════════════════════════════════════════════════╗
║             CONTEXT ASSEMBLY PERFORMANCE                  ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Assembly Stats:                                          ║
║  ├─ Total Assemblies: {total:>6}                              ║
║  └─ Avg Time: {time:>6.1f}ms                                   ║
║                                                           ║
║  Token Usage:                                             ║
║  ├─ Avg Tokens: {avg_tok:>6.0f}                                ║
║  ├─ Max Tokens: {max_tok:>6}                                   ║
║  └─ Min Tokens: {min_tok:>6}                                   ║
║                                                           ║
║  Curation:                                                ║
║  ├─ Avg Units Curated: {curated:>6.1f}                         ║
║  ├─ Avg Units Selected: {selected:>6.1f}                       ║
║  └─ Selection Ratio: {ratio:>5.1f}%                            ║
║                                                           ║
║  Progressive Disclosure:                                  ║
║  ├─ Snippets Created: {snip_create:>6}                         ║
║  ├─ Snippets Loaded: {snip_load:>6}                            ║
║  └─ Load Rate: {load_rate:>5.1f}%                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """.format(
            total=c.total_assemblies,
            time=c.avg_assembly_time_ms,
            avg_tok=c.avg_context_tokens,
            max_tok=c.max_context_tokens,
            min_tok=c.min_context_tokens,
            curated=c.avg_units_curated,
            selected=c.avg_units_selected,
            ratio=c.selection_ratio * 100,
            snip_create=c.snippets_created,
            snip_load=c.snippets_loaded,
            load_rate=c.snippet_load_rate * 100
        )

        return viz

    def render_full_report(self) -> str:
        """Render complete metrics report."""
        report = "\n"
        report += self.render_memory_status()
        report += "\n"
        report += self.render_routing_performance()
        report += "\n"
        report += self.render_context_performance()
        report += "\n"

        return report

    def render_compact_summary(self) -> str:
        """Render a compact one-line summary."""
        m = self.collector.memory_metrics
        r = self.collector.routing_metrics

        s1_rate = (r.system1_routed / r.total_decisions * 100) if r.total_decisions > 0 else 0

        return (
            f"Memory: {m.total_memory_units} units | "
            f"Queries: {m.total_queries} | "
            f"S1 Usage: {s1_rate:.0f}% | "
            f"Tokens Saved: {r.total_tokens_saved} | "
            f"Cost Saved: ${r.estimated_cost_saved_usd:.2f}"
        )
