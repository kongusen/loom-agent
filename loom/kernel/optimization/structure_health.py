"""
Structure Health Assessment

Evaluates the health and efficiency of fractal node structures,
providing diagnostics and optimization recommendations.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Health Metrics
# ============================================================================

class HealthStatus(Enum):
    """Overall health status"""
    EXCELLENT = "excellent"     # 0.9 - 1.0
    GOOD = "good"              # 0.7 - 0.9
    FAIR = "fair"              # 0.5 - 0.7
    POOR = "poor"              # 0.3 - 0.5
    CRITICAL = "critical"      # 0.0 - 0.3


class HealthIssue(Enum):
    """Types of health issues"""
    UNBALANCED_TREE = "unbalanced_tree"
    EXCESSIVE_DEPTH = "excessive_depth"
    TOO_MANY_NODES = "too_many_nodes"
    UNDERUTILIZED = "underutilized"
    RESOURCE_HEAVY = "resource_heavy"
    LOW_PERFORMANCE = "low_performance"
    HIGH_FAILURE_RATE = "high_failure_rate"
    REDUNDANT_NODES = "redundant_nodes"


@dataclass
class HealthDiagnostic:
    """Diagnostic result for a specific issue"""
    issue: HealthIssue
    severity: float  # 0-1, higher is worse
    affected_nodes: list[str]
    description: str
    recommendation: str


@dataclass
class HealthReport:
    """Comprehensive health report"""
    timestamp: float
    overall_score: float  # 0-1
    status: HealthStatus
    total_nodes: int
    max_depth: int

    # Component scores
    balance_score: float = 0.0
    efficiency_score: float = 0.0
    performance_score: float = 0.0
    utilization_score: float = 0.0

    # Issues
    diagnostics: list[HealthDiagnostic] = field(default_factory=list)

    # Recommendations
    top_recommendations: list[str] = field(default_factory=list)

    def get_status(self) -> HealthStatus:
        """Determine status from overall score"""
        if self.overall_score >= 0.9:
            return HealthStatus.EXCELLENT
        elif self.overall_score >= 0.7:
            return HealthStatus.GOOD
        elif self.overall_score >= 0.5:
            return HealthStatus.FAIR
        elif self.overall_score >= 0.3:
            return HealthStatus.POOR
        else:
            return HealthStatus.CRITICAL


# ============================================================================
# Structure Health Assessor
# ============================================================================

class StructureHealthAssessor:
    """
    Assesses fractal structure health and provides diagnostics
    """

    def __init__(
        self,
        balance_weight: float = 0.25,
        efficiency_weight: float = 0.25,
        performance_weight: float = 0.30,
        utilization_weight: float = 0.20
    ):
        """
        Initialize assessor

        Args:
            balance_weight: Weight for structure balance
            efficiency_weight: Weight for resource efficiency
            performance_weight: Weight for task performance
            utilization_weight: Weight for node utilization
        """
        self.balance_weight = balance_weight
        self.efficiency_weight = efficiency_weight
        self.performance_weight = performance_weight
        self.utilization_weight = utilization_weight

        # Normalize weights
        total = (balance_weight + efficiency_weight +
                performance_weight + utilization_weight)
        self.balance_weight /= total
        self.efficiency_weight /= total
        self.performance_weight /= total
        self.utilization_weight /= total

    def assess(
        self,
        root: Any,
        target_config: Any | None = None
    ) -> HealthReport:
        """
        Perform comprehensive health assessment

        Args:
            root: Root node of structure
            target_config: Target FractalConfig (for comparison)

        Returns:
            HealthReport with diagnostics and recommendations
        """
        import time

        # Collect structure data
        structure_data = self._collect_structure_data(root)

        # Compute component scores
        balance_score = self._assess_balance(structure_data, target_config)
        efficiency_score = self._assess_efficiency(structure_data)
        performance_score = self._assess_performance(structure_data)
        utilization_score = self._assess_utilization(structure_data)

        # Compute overall score
        overall_score = (
            balance_score * self.balance_weight +
            efficiency_score * self.efficiency_weight +
            performance_score * self.performance_weight +
            utilization_score * self.utilization_weight
        )

        # Run diagnostics
        diagnostics = self._run_diagnostics(structure_data, target_config)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            diagnostics,
            structure_data,
            target_config
        )

        # Create report
        report = HealthReport(
            timestamp=time.time(),
            overall_score=overall_score,
            status=HealthStatus.EXCELLENT,  # Will be set below
            total_nodes=structure_data['total_nodes'],
            max_depth=structure_data['max_depth'],
            balance_score=balance_score,
            efficiency_score=efficiency_score,
            performance_score=performance_score,
            utilization_score=utilization_score,
            diagnostics=diagnostics,
            top_recommendations=recommendations[:5]  # Top 5
        )

        report.status = report.get_status()

        return report

    # ========================================================================
    # Data Collection
    # ========================================================================

    def _collect_structure_data(self, root: Any) -> dict[str, Any]:
        """Collect comprehensive structure data"""
        nodes = []
        depths = []
        branching_factors = []
        fitness_scores = []
        token_usage = []
        execution_times = []
        success_counts = []
        task_counts = []

        def _collect(node: Any, depth: int = 0):
            nodes.append(node)
            depths.append(depth)

            # Metrics
            if node.metrics.task_count > 0:
                fitness_scores.append(node.metrics.fitness_score())
                token_usage.append(node.metrics.avg_tokens)
                execution_times.append(node.metrics.avg_time)
                success_counts.append(node.metrics.success_count)
                task_counts.append(node.metrics.task_count)

            # Children
            if node.children:
                branching_factors.append(len(node.children))
                for child in node.children:
                    _collect(child, depth + 1)

        _collect(root)

        return {
            'nodes': nodes,
            'total_nodes': len(nodes),
            'depths': depths,
            'max_depth': max(depths) if depths else 0,
            'avg_depth': sum(depths) / len(depths) if depths else 0,
            'branching_factors': branching_factors,
            'avg_branching': sum(branching_factors) / len(branching_factors) if branching_factors else 0,
            'fitness_scores': fitness_scores,
            'avg_fitness': sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0,
            'min_fitness': min(fitness_scores) if fitness_scores else 0,
            'max_fitness': max(fitness_scores) if fitness_scores else 0,
            'token_usage': token_usage,
            'avg_tokens': sum(token_usage) / len(token_usage) if token_usage else 0,
            'execution_times': execution_times,
            'avg_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'task_counts': task_counts,
            'total_tasks': sum(task_counts) if task_counts else 0,
            'success_counts': success_counts,
            'total_successes': sum(success_counts) if success_counts else 0
        }

    # ========================================================================
    # Component Assessments
    # ========================================================================

    def _assess_balance(
        self,
        data: dict[str, Any],
        config: Any | None
    ) -> float:
        """Assess structure balance (0-1, higher is better)"""
        score = 1.0

        # Factor 1: Depth variation (penalize unbalanced tree)
        if data['depths']:
            depth_variance = sum(
                (d - data['avg_depth']) ** 2 for d in data['depths']
            ) / len(data['depths'])
            depth_penalty = min(depth_variance / 10, 0.3)  # Max 0.3 penalty
            score -= depth_penalty

        # Factor 2: Branching consistency
        if data['branching_factors']:
            branching_variance = sum(
                (b - data['avg_branching']) ** 2 for b in data['branching_factors']
            ) / len(data['branching_factors'])
            branching_penalty = min(branching_variance / 10, 0.2)  # Max 0.2 penalty
            score -= branching_penalty

        # Factor 3: Depth within limits
        if config and hasattr(config, 'max_depth') and data['max_depth'] > config.max_depth:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _assess_efficiency(self, data: dict[str, Any]) -> float:
        """Assess resource efficiency (0-1, higher is better)"""
        if not data['token_usage']:
            return 1.0

        score = 1.0

        # Factor 1: Token efficiency
        avg_tokens = data['avg_tokens']
        if avg_tokens > 8000:  # High usage
            score -= 0.3
        elif avg_tokens > 4000:
            score -= 0.1

        # Factor 2: Time efficiency
        avg_time = data['avg_time']
        if avg_time > 20:  # Slow
            score -= 0.3
        elif avg_time > 10:
            score -= 0.1

        # Factor 3: Nodes per task (fewer nodes = more efficient)
        if data['total_tasks'] > 0:
            nodes_per_task = data['total_nodes'] / data['total_tasks']
            if nodes_per_task > 3:
                score -= 0.2
            elif nodes_per_task > 2:
                score -= 0.1

        return max(0.0, min(1.0, score))

    def _assess_performance(self, data: dict[str, Any]) -> float:
        """Assess task performance (0-1, higher is better)"""
        if not data['fitness_scores']:
            return 0.5  # Neutral

        # Average fitness is the primary indicator
        return data['avg_fitness']

    def _assess_utilization(self, data: dict[str, Any]) -> float:
        """Assess node utilization (0-1, higher is better)"""
        if not data['nodes']:
            return 0.0

        score = 1.0

        # Factor 1: Idle nodes (nodes with no tasks)
        idle_nodes = sum(1 for n in data['nodes'] if n.metrics.task_count == 0)
        idle_ratio = idle_nodes / data['total_nodes']
        score -= idle_ratio * 0.5  # Penalize heavily

        # Factor 2: Low-activity nodes (< 3 tasks)
        low_activity = sum(
            1 for n in data['nodes']
            if 0 < n.metrics.task_count < 3
        )
        low_activity_ratio = low_activity / data['total_nodes']
        score -= low_activity_ratio * 0.3

        return max(0.0, min(1.0, score))

    # ========================================================================
    # Diagnostics
    # ========================================================================

    def _run_diagnostics(
        self,
        data: dict[str, Any],
        config: Any | None
    ) -> list[HealthDiagnostic]:
        """Run diagnostic checks"""
        diagnostics = []

        # Diagnostic 1: Unbalanced tree
        if data['depths']:
            max_depth = data['max_depth']
            min_depth = min(data['depths'])
            if max_depth - min_depth > 2:
                affected = [
                    n.node_id for n in data['nodes']
                    if self._get_node_depth(n, data['nodes']) == max_depth
                ]
                diagnostics.append(HealthDiagnostic(
                    issue=HealthIssue.UNBALANCED_TREE,
                    severity=0.6,
                    affected_nodes=affected[:10],
                    description=f"Tree depth varies from {min_depth} to {max_depth}",
                    recommendation="Consider rebalancing by redistributing subtasks"
                ))

        # Diagnostic 2: Excessive depth
        if config and hasattr(config, 'max_depth') and data['max_depth'] > config.max_depth:
            diagnostics.append(HealthDiagnostic(
                issue=HealthIssue.EXCESSIVE_DEPTH,
                severity=0.8,
                affected_nodes=[],
                description=f"Max depth {data['max_depth']} exceeds limit {config.max_depth}",
                recommendation="Prune deep branches or increase max_depth limit"
            ))

        # Diagnostic 3: Underutilized nodes
        idle_nodes = [n for n in data['nodes'] if n.metrics.task_count == 0]
        if len(idle_nodes) > data['total_nodes'] * 0.3:
            diagnostics.append(HealthDiagnostic(
                issue=HealthIssue.UNDERUTILIZED,
                severity=0.7,
                affected_nodes=[n.node_id for n in idle_nodes[:10]],
                description=f"{len(idle_nodes)} nodes have no task history",
                recommendation="Prune unused nodes or redistribute tasks"
            ))

        # Diagnostic 4: Low performance nodes
        low_perf = [
            n for n in data['nodes']
            if n.metrics.task_count > 3 and n.metrics.fitness_score() < 0.4
        ]
        if low_perf:
            diagnostics.append(HealthDiagnostic(
                issue=HealthIssue.LOW_PERFORMANCE,
                severity=0.8,
                affected_nodes=[n.node_id for n in low_perf[:10]],
                description=f"{len(low_perf)} nodes have low fitness scores",
                recommendation="Prune or optimize low-performing nodes"
            ))

        # Diagnostic 5: Resource heavy
        if data['avg_tokens'] > 6000:
            heavy_nodes = [
                n for n in data['nodes']
                if n.metrics.task_count > 0 and n.metrics.avg_tokens > 8000
            ]
            if heavy_nodes:
                diagnostics.append(HealthDiagnostic(
                    issue=HealthIssue.RESOURCE_HEAVY,
                    severity=0.6,
                    affected_nodes=[n.node_id for n in heavy_nodes[:10]],
                    description=f"{len(heavy_nodes)} nodes use excessive tokens",
                    recommendation="Optimize prompts or split heavy tasks"
                ))

        # Sort by severity
        diagnostics.sort(key=lambda d: d.severity, reverse=True)

        return diagnostics

    def _get_node_depth(self, node: Any, all_nodes: list[Any]) -> int:
        """Get depth of a node"""
        depth = 0
        current = node
        while current.parent is not None:
            depth += 1
            current = current.parent
        return depth

    # ========================================================================
    # Recommendations
    # ========================================================================

    def _generate_recommendations(
        self,
        diagnostics: list[HealthDiagnostic],
        data: dict[str, Any],
        config: Any | None
    ) -> list[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # From diagnostics
        for diag in diagnostics:
            if diag.severity > 0.5:
                recommendations.append(
                    f"[{diag.issue.value.upper()}] {diag.recommendation}"
                )

        # General recommendations based on data

        # Low overall performance
        if data['avg_fitness'] < 0.6:
            recommendations.append(
                "Overall performance is below target. Consider enabling auto-pruning "
                "to remove underperforming nodes."
            )

        # High resource usage
        if data['avg_tokens'] > 5000:
            recommendations.append(
                f"Average token usage ({data['avg_tokens']:.0f}) is high. "
                "Review prompts and consider using System 1 for simpler tasks."
            )

        # Too many nodes
        if data['total_nodes'] > 15:
            recommendations.append(
                f"Structure has {data['total_nodes']} nodes which may be excessive. "
                "Consider increasing complexity_threshold to reduce auto-growth."
            )

        # Unbalanced branching
        if data['branching_factors']:
            max_branch = max(data['branching_factors'])
            if max_branch > 5:
                recommendations.append(
                    f"Some nodes have {max_branch} children. "
                    "Consider reducing max_children limit for better balance."
                )

        return recommendations

    # ========================================================================
    # Reporting
    # ========================================================================

    def format_report(self, report: HealthReport) -> str:
        """Format health report as readable text"""
        lines = []

        # Header
        status_emoji = {
            HealthStatus.EXCELLENT: "🟢",
            HealthStatus.GOOD: "🟡",
            HealthStatus.FAIR: "🟠",
            HealthStatus.POOR: "🔴",
            HealthStatus.CRITICAL: "🆘"
        }

        lines.append("=" * 70)
        lines.append(f"{status_emoji[report.status]} STRUCTURE HEALTH REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Overall
        lines.append(f"Overall Score: {report.overall_score:.2f} ({report.status.value.upper()})")
        lines.append(f"Total Nodes: {report.total_nodes}")
        lines.append(f"Max Depth: {report.max_depth}")
        lines.append("")

        # Component scores
        lines.append("Component Scores:")
        lines.append(f"  Balance:      {report.balance_score:.2f} {'▓' * int(report.balance_score * 10)}{'░' * (10 - int(report.balance_score * 10))}")
        lines.append(f"  Efficiency:   {report.efficiency_score:.2f} {'▓' * int(report.efficiency_score * 10)}{'░' * (10 - int(report.efficiency_score * 10))}")
        lines.append(f"  Performance:  {report.performance_score:.2f} {'▓' * int(report.performance_score * 10)}{'░' * (10 - int(report.performance_score * 10))}")
        lines.append(f"  Utilization:  {report.utilization_score:.2f} {'▓' * int(report.utilization_score * 10)}{'░' * (10 - int(report.utilization_score * 10))}")
        lines.append("")

        # Diagnostics
        if report.diagnostics:
            lines.append(f"Issues Found: {len(report.diagnostics)}")
            lines.append("")
            for i, diag in enumerate(report.diagnostics[:5], 1):
                severity_bar = "🔴" * int(diag.severity * 5)
                lines.append(f"{i}. {diag.issue.value.upper()} {severity_bar}")
                lines.append(f"   {diag.description}")
                if diag.affected_nodes:
                    lines.append(f"   Affected: {', '.join(diag.affected_nodes[:3])}...")
                lines.append("")

        # Recommendations
        if report.top_recommendations:
            lines.append("Top Recommendations:")
            for i, rec in enumerate(report.top_recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)
