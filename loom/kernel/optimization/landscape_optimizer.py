"""
Fitness Landscape Optimizer

Learns optimal structure patterns from historical performance data
and provides intelligent recommendations for structure optimization.
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from loom.config.fractal import GrowthStrategy

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class StructureSnapshot:
    """Snapshot of a structure at a point in time"""

    timestamp: float
    structure_id: str
    task_type: str
    task_complexity: float

    # Structure topology
    total_nodes: int
    max_depth: int
    avg_depth: float
    avg_branching: float
    node_roles: dict[str, int]  # role -> count

    # Performance metrics
    fitness_score: float
    success_rate: float
    avg_tokens: float
    avg_time: float
    avg_cost: float

    # Strategy info
    growth_strategies: dict[str, int]  # strategy -> count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp,
            "structure_id": self.structure_id,
            "task_type": self.task_type,
            "task_complexity": self.task_complexity,
            "topology": {
                "total_nodes": self.total_nodes,
                "max_depth": self.max_depth,
                "avg_depth": self.avg_depth,
                "avg_branching": self.avg_branching,
                "node_roles": self.node_roles,
            },
            "performance": {
                "fitness_score": self.fitness_score,
                "success_rate": self.success_rate,
                "avg_tokens": self.avg_tokens,
                "avg_time": self.avg_time,
                "avg_cost": self.avg_cost,
            },
            "strategies": self.growth_strategies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructureSnapshot":
        """Create from dictionary"""
        return cls(
            timestamp=data["timestamp"],
            structure_id=data["structure_id"],
            task_type=data["task_type"],
            task_complexity=data["task_complexity"],
            total_nodes=data["topology"]["total_nodes"],
            max_depth=data["topology"]["max_depth"],
            avg_depth=data["topology"]["avg_depth"],
            avg_branching=data["topology"]["avg_branching"],
            node_roles=data["topology"]["node_roles"],
            fitness_score=data["performance"]["fitness_score"],
            success_rate=data["performance"]["success_rate"],
            avg_tokens=data["performance"]["avg_tokens"],
            avg_time=data["performance"]["avg_time"],
            avg_cost=data["performance"]["avg_cost"],
            growth_strategies=data["strategies"],
        )


@dataclass
class StructurePattern:
    """Learned optimal structure pattern"""

    pattern_id: str
    task_pattern: str  # Regex or description
    avg_fitness: float
    usage_count: int

    # Optimal topology
    recommended_depth: int
    recommended_branching: float
    recommended_roles: dict[str, float]  # role -> proportion
    recommended_strategies: list[GrowthStrategy]

    # Performance guarantees
    min_fitness: float
    max_tokens: float
    success_rate: float

    confidence: float = 0.0  # How confident we are in this pattern

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pattern_id": self.pattern_id,
            "task_pattern": self.task_pattern,
            "avg_fitness": self.avg_fitness,
            "usage_count": self.usage_count,
            "topology": {
                "recommended_depth": self.recommended_depth,
                "recommended_branching": self.recommended_branching,
                "recommended_roles": self.recommended_roles,
                "recommended_strategies": [s.value for s in self.recommended_strategies],
            },
            "performance": {
                "min_fitness": self.min_fitness,
                "max_tokens": self.max_tokens,
                "success_rate": self.success_rate,
            },
            "confidence": self.confidence,
        }


# ============================================================================
# Fitness Landscape Optimizer
# ============================================================================


class FitnessLandscapeOptimizer:
    """
    Learns optimal structure configurations from historical performance data

    This optimizer:
    1. Records structure performance snapshots
    2. Analyzes patterns in successful structures
    3. Recommends optimal configurations for new tasks
    4. Visualizes the fitness landscape
    """

    def __init__(
        self,
        memory_size: int = 1000,
        min_samples_for_pattern: int = 5,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize landscape optimizer

        Args:
            memory_size: Maximum snapshots to keep
            min_samples_for_pattern: Minimum samples to learn a pattern
            confidence_threshold: Minimum confidence for recommendations
        """
        self.memory_size = memory_size
        self.min_samples_for_pattern = min_samples_for_pattern
        self.confidence_threshold = confidence_threshold

        # Performance history
        self.snapshots: list[StructureSnapshot] = []

        # Learned patterns
        self.patterns: dict[str, StructurePattern] = {}

        # Landscape data (for visualization)
        self.landscape_data: dict[tuple[int, int], list[float]] = defaultdict(list)
        # Key: (complexity_bin, depth_bin), Value: list of fitness scores

    # ========================================================================
    # Recording Performance
    # ========================================================================

    def record_structure_performance(
        self,
        root: Any,  # FractalAgentNode
        task_type: str,
        task_complexity: float,
        structure_id: str | None = None,
    ) -> StructureSnapshot:
        """
        Record a structure's performance

        Args:
            root: Root node of structure
            task_type: Type/category of task
            task_complexity: Complexity score (0-1)
            structure_id: Optional unique ID

        Returns:
            Created snapshot
        """
        # Collect structure data
        topology = self._analyze_topology(root)
        performance = self._analyze_performance(root)
        strategies = self._analyze_strategies(root)

        # Create snapshot
        snapshot = StructureSnapshot(
            timestamp=time.time(),
            structure_id=structure_id or f"struct_{int(time.time())}_{id(root)}",
            task_type=task_type,
            task_complexity=task_complexity,
            **topology,
            **performance,
            growth_strategies=strategies,
        )

        # Add to history
        self.snapshots.append(snapshot)

        # Trim if needed
        if len(self.snapshots) > self.memory_size:
            self.snapshots = self.snapshots[-self.memory_size :]

        # Update landscape data
        complexity_bin = int(task_complexity * 10)  # 0-10
        depth_bin = snapshot.max_depth
        self.landscape_data[(complexity_bin, depth_bin)].append(snapshot.fitness_score)

        logger.info(
            f"Recorded structure performance: {snapshot.structure_id}, "
            f"fitness={snapshot.fitness_score:.2f}"
        )

        return snapshot

    def _analyze_topology(self, root: Any) -> dict[str, Any]:
        """Analyze structure topology"""
        nodes = []
        depths = []
        branching_factors = []
        role_counts: defaultdict[str, int] = defaultdict(int)

        def _collect(node: Any, depth: int = 0):
            nodes.append(node)
            depths.append(depth)
            role_counts[node.role.value] += 1

            if node.children:
                branching_factors.append(len(node.children))
                for child in node.children:
                    _collect(child, depth + 1)

        _collect(root)

        return {
            "total_nodes": len(nodes),
            "max_depth": max(depths) if depths else 0,
            "avg_depth": sum(depths) / len(depths) if depths else 0,
            "avg_branching": sum(branching_factors) / len(branching_factors)
            if branching_factors
            else 0,
            "node_roles": dict(role_counts),
        }

    def _analyze_performance(self, root: Any) -> dict[str, Any]:
        """Analyze structure performance"""
        nodes = []

        def _collect(node: Any):
            if node.metrics.task_count > 0:
                nodes.append(node)
            for child in node.children:
                _collect(child)

        _collect(root)

        if not nodes:
            return {
                "fitness_score": 0.0,
                "success_rate": 0.0,
                "avg_tokens": 0.0,
                "avg_time": 0.0,
                "avg_cost": 0.0,
            }

        fitness_scores = [n.metrics.fitness_score() for n in nodes]
        success_rates = [n.metrics.success_rate for n in nodes]
        avg_tokens = [n.metrics.avg_tokens for n in nodes]
        avg_times = [n.metrics.avg_time for n in nodes]
        avg_costs = [n.metrics.avg_cost for n in nodes]

        return {
            "fitness_score": sum(fitness_scores) / len(fitness_scores),
            "success_rate": sum(success_rates) / len(success_rates),
            "avg_tokens": sum(avg_tokens) / len(avg_tokens),
            "avg_time": sum(avg_times) / len(avg_times),
            "avg_cost": sum(avg_costs) / len(avg_costs),
        }

    def _analyze_strategies(self, _root: Any) -> dict[str, int]:
        """Analyze growth strategies used"""
        # This would require tracking strategy history in nodes
        # For now, return empty
        return {}

    # ========================================================================
    # Pattern Learning
    # ========================================================================

    def learn_patterns(self, task_type_filter: str | None = None) -> list[StructurePattern]:
        """
        Learn optimal patterns from historical data

        Args:
            task_type_filter: Optional filter by task type

        Returns:
            List of learned patterns
        """
        # Group snapshots by task type
        task_groups = defaultdict(list)
        for snapshot in self.snapshots:
            if task_type_filter and snapshot.task_type != task_type_filter:
                continue
            task_groups[snapshot.task_type].append(snapshot)

        new_patterns = []

        for task_type, snapshots in task_groups.items():
            if len(snapshots) < self.min_samples_for_pattern:
                continue

            # Find high-performing snapshots
            high_performers = [
                s
                for s in snapshots
                if s.fitness_score >= 0.7  # High fitness threshold
            ]

            if not high_performers:
                continue

            # Extract pattern
            pattern = self._extract_pattern(task_type, high_performers)
            self.patterns[pattern.pattern_id] = pattern
            new_patterns.append(pattern)

            logger.info(
                f"Learned pattern: {pattern.pattern_id} with "
                f"{len(high_performers)} high-performing examples"
            )

        return new_patterns

    def _extract_pattern(
        self, task_type: str, snapshots: list[StructureSnapshot]
    ) -> StructurePattern:
        """Extract optimal pattern from snapshots"""
        # Aggregate statistics
        avg_fitness = sum(s.fitness_score for s in snapshots) / len(snapshots)
        min_fitness = min(s.fitness_score for s in snapshots)
        avg_tokens = sum(s.avg_tokens for s in snapshots) / len(snapshots)
        success_rate = sum(s.success_rate for s in snapshots) / len(snapshots)

        # Optimal topology
        depths = [s.max_depth for s in snapshots]
        branchings = [s.avg_branching for s in snapshots]
        recommended_depth = int(np.median(depths))
        recommended_branching = float(np.median(branchings))

        # Role distribution
        all_roles = defaultdict(list)
        for s in snapshots:
            total = s.total_nodes
            for role, count in s.node_roles.items():
                all_roles[role].append(count / total if total > 0 else 0)

        recommended_roles = {
            role: float(np.median(proportions)) for role, proportions in all_roles.items()
        }

        # Confidence based on sample size and consistency
        confidence = min(1.0, len(snapshots) / 20) * (min_fitness / avg_fitness)

        return StructurePattern(
            pattern_id=f"pattern_{task_type}_{int(time.time())}",
            task_pattern=task_type,
            avg_fitness=avg_fitness,
            usage_count=len(snapshots),
            recommended_depth=recommended_depth,
            recommended_branching=recommended_branching,
            recommended_roles=recommended_roles,
            recommended_strategies=[],  # TODO: extract from snapshots
            min_fitness=min_fitness,
            max_tokens=avg_tokens,
            success_rate=success_rate,
            confidence=confidence,
        )

    # ========================================================================
    # Recommendations
    # ========================================================================

    def recommend_structure(
        self,
        task_type: str,
        task_complexity: float,  # noqa: ARG002 - Reserved for future complexity-based filtering
        current_fitness: float | None = None,
    ) -> StructurePattern | None:
        """
        Recommend optimal structure configuration for a task

        Args:
            task_type: Type of task
            task_complexity: Task complexity (0-1)
            current_fitness: Current fitness (if any)

        Returns:
            Recommended pattern or None
        """
        # Find matching patterns
        candidates = [
            p
            for p in self.patterns.values()
            if self._task_matches_pattern(task_type, p.task_pattern)
            and p.confidence >= self.confidence_threshold
        ]

        if not candidates:
            logger.info(f"No patterns found for task type: {task_type}")
            return None

        # If current fitness provided, filter for improvements
        if current_fitness is not None:
            candidates = [
                p
                for p in candidates
                if p.avg_fitness > current_fitness + 0.1  # Require 10% improvement
            ]

        if not candidates:
            logger.info(f"No better patterns found (current fitness: {current_fitness:.2f})")
            return None

        # Return best pattern
        best = max(candidates, key=lambda p: p.avg_fitness * p.confidence)

        logger.info(
            f"Recommended pattern: {best.pattern_id} "
            f"(fitness={best.avg_fitness:.2f}, confidence={best.confidence:.2f})"
        )

        return best

    def _task_matches_pattern(self, task_type: str, pattern: str) -> bool:
        """Check if task matches pattern"""
        # Simple string matching for now
        # Could use regex or semantic similarity
        return task_type.lower() in pattern.lower() or pattern.lower() in task_type.lower()

    # ========================================================================
    # Landscape Visualization
    # ========================================================================

    def visualize_landscape(
        self,
        _complexity_range: tuple[float, float] = (0.0, 1.0),
        depth_range: tuple[int, int] = (0, 5),
    ) -> str:
        """
        Visualize fitness landscape

        Args:
            complexity_range: Range of complexity to show
            depth_range: Range of depth to show

        Returns:
            ASCII visualization
        """
        lines = []
        lines.append("=" * 70)
        lines.append("FITNESS LANDSCAPE")
        lines.append("=" * 70)
        lines.append("")
        lines.append("Complexity (x-axis) vs Depth (y-axis) vs Fitness (color)")
        lines.append("")

        # Create grid
        complexity_bins = 10
        depth_bins = depth_range[1] - depth_range[0] + 1

        grid = np.zeros((depth_bins, complexity_bins))
        counts = np.zeros((depth_bins, complexity_bins))

        # Fill grid
        for (c_bin, d_bin), fitnesses in self.landscape_data.items():
            if depth_range[0] <= d_bin <= depth_range[1]:
                d_idx = d_bin - depth_range[0]
                if 0 <= c_bin < complexity_bins:
                    grid[d_idx, c_bin] = np.mean(fitnesses)
                    counts[d_idx, c_bin] = len(fitnesses)

        # Render
        lines.append("    " + "".join(f"{i:4d}" for i in range(complexity_bins)))
        lines.append("   +" + "-" * (complexity_bins * 4))

        for d in range(depth_bins):
            row = f"{d:2d} |"
            for c in range(complexity_bins):
                if counts[d, c] > 0:
                    fitness = grid[d, c]
                    char = self._fitness_to_char(fitness)
                    row += f" {char}  "
                else:
                    row += "    "
            lines.append(row)

        lines.append("")
        lines.append("Legend: █=0.9+ ▓=0.7+ ▒=0.5+ ░=0.3+ ·=<0.3  =no data")
        lines.append("")

        # Add statistics
        if self.landscape_data:
            all_fitnesses = [f for fitnesses in self.landscape_data.values() for f in fitnesses]
            lines.append(f"Total samples: {len(all_fitnesses)}")
            lines.append(f"Average fitness: {np.mean(all_fitnesses):.2f}")
            lines.append(f"Best fitness: {np.max(all_fitnesses):.2f}")
            lines.append(f"Worst fitness: {np.min(all_fitnesses):.2f}")

        lines.append("=" * 70)

        return "\n".join(lines)

    def _fitness_to_char(self, fitness: float) -> str:
        """Convert fitness to visualization character"""
        if fitness >= 0.9:
            return "█"
        elif fitness >= 0.7:
            return "▓"
        elif fitness >= 0.5:
            return "▒"
        elif fitness >= 0.3:
            return "░"
        else:
            return "·"

    # ========================================================================
    # Analysis
    # ========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get optimizer statistics"""
        if not self.snapshots:
            return {"total_snapshots": 0, "patterns_learned": 0}

        fitnesses = [s.fitness_score for s in self.snapshots]

        return {
            "total_snapshots": len(self.snapshots),
            "patterns_learned": len(self.patterns),
            "avg_fitness": np.mean(fitnesses),
            "best_fitness": np.max(fitnesses),
            "worst_fitness": np.min(fitnesses),
            "fitness_std": np.std(fitnesses),
            "task_types": len({s.task_type for s in self.snapshots}),
        }

    def get_best_structures(
        self, task_type: str | None = None, limit: int = 5
    ) -> list[StructureSnapshot]:
        """Get best performing structures"""
        snapshots = self.snapshots

        if task_type:
            snapshots = [s for s in snapshots if s.task_type == task_type]

        # Sort by fitness
        snapshots = sorted(snapshots, key=lambda s: s.fitness_score, reverse=True)

        return snapshots[:limit]

    # ========================================================================
    # Persistence
    # ========================================================================

    def save(self, filepath: str):
        """Save optimizer state to file"""
        data = {
            "snapshots": [s.to_dict() for s in self.snapshots],
            "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
            "landscape_data": {f"{k[0]}_{k[1]}": v for k, v in self.landscape_data.items()},
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved optimizer state to {filepath}")

    def load(self, filepath: str):
        """Load optimizer state from file"""
        with open(filepath) as f:
            data = json.load(f)

        self.snapshots = [StructureSnapshot.from_dict(s) for s in data["snapshots"]]

        self.patterns = {}
        for k, v in data["patterns"].items():
            pattern = StructurePattern(
                pattern_id=v["pattern_id"],
                task_pattern=v["task_pattern"],
                avg_fitness=v["avg_fitness"],
                usage_count=v["usage_count"],
                recommended_depth=v["topology"]["recommended_depth"],
                recommended_branching=v["topology"]["recommended_branching"],
                recommended_roles=v["topology"]["recommended_roles"],
                recommended_strategies=[
                    GrowthStrategy[s.upper()]
                    if hasattr(GrowthStrategy, s.upper())
                    else GrowthStrategy.DECOMPOSE
                    for s in v["topology"]["recommended_strategies"]
                ],
                min_fitness=v["performance"]["min_fitness"],
                max_tokens=v["performance"]["max_tokens"],
                success_rate=v["performance"]["success_rate"],
                confidence=v["confidence"],
            )
            self.patterns[k] = pattern

        self.landscape_data = defaultdict(list)
        for key_str, fitnesses in data["landscape_data"].items():
            c, d = map(int, key_str.split("_"))
            self.landscape_data[(c, d)] = fitnesses

        logger.info(f"Loaded optimizer state from {filepath}")
