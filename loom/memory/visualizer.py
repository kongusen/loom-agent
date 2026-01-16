"""
Visualization and Reporting for LoomMemory Metrics
"""

from .metrics import MetricsCollector


class MetricsVisualizer:
    """
    Generates human-readable visualizations of metrics.
    """

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def render_memory_status(self) -> str:
        """Render memory tier status as ASCII art."""
        m = self.collector.memory_metrics

        viz = f"""
╔═══════════════════════════════════════════════════════════╗
║                  LOOM MEMORY STATUS                       ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  L4 Global Knowledge                                      ║
║  ├─ Size: {m.current_l4_size:>4} units                                    ║
║  ├─ Promotions: {m.l4_promotions:>4}                                   ║
║  └─ Vector Searches: {m.vector_searches:>4}                            ║
║                                                           ║
║  ─────────────────────────────────────────────────────    ║
║                                                           ║
║  L3 Session History                                       ║
║  ├─ Size: {m.current_l3_size:>4} units                                    ║
║  └─ Compressions: {m.compressions_performed:>4}                                 ║
║                                                           ║
║  ─────────────────────────────────────────────────────    ║
║                                                           ║
║  L2 Working Memory                                        ║
║  └─ Size: {m.current_l2_size:>4} units                                    ║
║                                                           ║
║  ─────────────────────────────────────────────────────    ║
║                                                           ║
║  L1 Raw IO Buffer                                         ║
║  ├─ Size: {m.current_l1_size:>4} units                                    ║
║  └─ Evictions: {m.l1_evictions:>4}                                    ║
║                                                           ║
╠═══════════════════════════════════════════════════════════╣
║  Total Units: {m.total_memory_units:>4}  |  Total Queries: {m.total_queries:>6}        ║
╚═══════════════════════════════════════════════════════════╝
        """

        return viz

    def render_routing_performance(self) -> str:
        """Render System 1/2 routing performance."""
        r = self.collector.routing_metrics

        s1_success_rate = (r.s1_successes / r.s1_calls * 100) if r.s1_calls > 0 else 0
        s1_usage_rate = (r.system1_routed / r.total_decisions * 100) if r.total_decisions > 0 else 0

        viz = f"""
╔═══════════════════════════════════════════════════════════╗
║              SYSTEM 1/2 ROUTING PERFORMANCE               ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Routing Decisions:                                       ║
║  ├─ Total: {r.total_decisions:>6}                                          ║
║  ├─ System 1: {r.system1_routed:>6} ({s1_usage_rate:>5.1f}%)                            ║
║  ├─ System 2: {r.system2_routed:>6} ({(r.system2_routed / r.total_decisions * 100) if r.total_decisions > 0 else 0:>5.1f}%)                            ║
║  └─ Adaptive: {r.adaptive_routed:>6}                                         ║
║                                                           ║
║  System 1 Performance:                                    ║
║  ├─ Calls: {r.s1_calls:>6}                                       ║
║  ├─ Success Rate: {s1_success_rate:>5.1f}%                            ║
║  ├─ Avg Confidence: {r.s1_avg_confidence:>5.2f}                             ║
║  ├─ Avg Time: {r.s1_avg_time_ms:>6.1f}ms                                 ║
║  └─ Avg Tokens: {r.s1_avg_tokens:>6.0f}                                  ║
║                                                           ║
║  System 2 Performance:                                    ║
║  ├─ Calls: {r.s2_calls:>6}                                       ║
║  ├─ Avg Time: {r.s2_avg_time_ms:>6.1f}ms                                 ║
║  └─ Avg Tokens: {r.s2_avg_tokens:>6.0f}                                  ║
║                                                           ║
║  Adaptive Fallback:                                       ║
║  ├─ S1→S2 Switches: {r.s1_to_s2_switches:>6}                              ║
║  └─ Switch Rate: {r.switch_rate * 100:>5.1f}%                            ║
║                                                           ║
║  Cost Savings:                                            ║
║  ├─ Tokens Saved: {r.total_tokens_saved:>8}                            ║
║  └─ Est. Cost Saved: ${r.estimated_cost_saved_usd:>7.2f}                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """

        return viz

    def render_context_performance(self) -> str:
        """Render context assembly performance."""
        c = self.collector.context_metrics

        viz = f"""
╔═══════════════════════════════════════════════════════════╗
║             CONTEXT ASSEMBLY PERFORMANCE                  ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Assembly Stats:                                          ║
║  ├─ Total Assemblies: {c.total_assemblies:>6}                              ║
║  └─ Avg Time: {c.avg_assembly_time_ms:>6.1f}ms                                   ║
║                                                           ║
║  Token Usage:                                             ║
║  ├─ Avg Tokens: {c.avg_context_tokens:>6.0f}                                ║
║  ├─ Max Tokens: {c.max_context_tokens:>6}                                   ║
║  └─ Min Tokens: {c.min_context_tokens:>6}                                   ║
║                                                           ║
║  Curation:                                                ║
║  ├─ Avg Units Curated: {c.avg_units_curated:>6.1f}                         ║
║  ├─ Avg Units Selected: {c.avg_units_selected:>6.1f}                       ║
║  └─ Selection Ratio: {c.selection_ratio * 100:>5.1f}%                            ║
║                                                           ║
║  Progressive Disclosure:                                  ║
║  ├─ Snippets Created: {c.snippets_created:>6}                         ║
║  ├─ Snippets Loaded: {c.snippets_loaded:>6}                            ║
║  └─ Load Rate: {c.snippet_load_rate * 100:>5.1f}%                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """

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
