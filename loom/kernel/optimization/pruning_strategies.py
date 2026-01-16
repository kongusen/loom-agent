"""
Intelligent Pruning Strategies

Advanced pruning algorithms for optimizing fractal structure performance.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PruningCriterion(Enum):
    """Criteria for pruning decisions"""
    LOW_FITNESS = "low_fitness"
    HIGH_FAILURE_RATE = "high_failure_rate"
    REDUNDANT = "redundant"
    IDLE = "idle"
    RESOURCE_HEAVY = "resource_heavy"
    DUPLICATE_FUNCTION = "duplicate_function"


@dataclass
class PruningDecision:
    """Result of pruning evaluation"""
    should_prune: bool
    confidence: float  # 0-1
    criteria: list[PruningCriterion]
    reason: str
    expected_impact: float  # Expected fitness improvement


class PruningStrategy(ABC):
    """Base class for pruning strategies"""

    @abstractmethod
    def evaluate(
        self,
        node: Any,
        parent: Any | None,
        siblings: list[Any],
        context: dict[str, Any]
    ) -> PruningDecision:
        """
        Evaluate if node should be pruned

        Args:
            node: Node to evaluate
            parent: Parent node
            siblings: Sibling nodes
            context: Additional context

        Returns:
            PruningDecision
        """
        pass


# ============================================================================
# Fitness-Based Pruning
# ============================================================================

class FitnessPruningStrategy(PruningStrategy):
    """Prune nodes with low fitness scores"""

    def __init__(
        self,
        fitness_threshold: float = 0.3,
        min_tasks: int = 3
    ):
        self.fitness_threshold = fitness_threshold
        self.min_tasks = min_tasks

    def evaluate(
        self,
        node: Any,
        _parent: Any | None,
        _siblings: list[Any],
        _context: dict[str, Any]
    ) -> PruningDecision:

        # Need minimum task count
        if node.metrics.task_count < self.min_tasks:
            return PruningDecision(
                should_prune=False,
                confidence=0.0,
                criteria=[],
                reason="Insufficient task history",
                expected_impact=0.0
            )

        fitness = node.metrics.fitness_score()

        if fitness < self.fitness_threshold:
            return PruningDecision(
                should_prune=True,
                confidence=0.9,
                criteria=[PruningCriterion.LOW_FITNESS],
                reason=f"Fitness {fitness:.2f} < threshold {self.fitness_threshold}",
                expected_impact=0.1  # Removing low performer
            )

        return PruningDecision(
            should_prune=False,
            confidence=0.0,
            criteria=[],
            reason="Fitness acceptable",
            expected_impact=0.0
        )


# ============================================================================
# Redundancy-Based Pruning
# ============================================================================

class RedundancyPruningStrategy(PruningStrategy):
    """Prune redundant nodes (parent/sibling does better)"""

    def __init__(
        self,
        fitness_gap_threshold: float = 0.2,
        min_tasks: int = 3
    ):
        self.fitness_gap_threshold = fitness_gap_threshold
        self.min_tasks = min_tasks

    def evaluate(
        self,
        node: Any,
        parent: Any | None,
        siblings: list[Any],
        _context: dict[str, Any]
    ) -> PruningDecision:

        if node.metrics.task_count < self.min_tasks:
            return PruningDecision(
                should_prune=False,
                confidence=0.0,
                criteria=[],
                reason="Insufficient task history",
                expected_impact=0.0
            )

        node_fitness = node.metrics.fitness_score()

        # Check against parent
        if parent and parent.metrics.task_count >= self.min_tasks:
            parent_fitness = parent.metrics.fitness_score()
            gap = parent_fitness - node_fitness

            if gap > self.fitness_gap_threshold:
                return PruningDecision(
                    should_prune=True,
                    confidence=0.8,
                    criteria=[PruningCriterion.REDUNDANT],
                    reason=f"Parent fitness {parent_fitness:.2f} >> node {node_fitness:.2f}",
                    expected_impact=0.05
                )

        # Check against siblings
        if siblings:
            sibling_fitnesses = [
                s.metrics.fitness_score()
                for s in siblings
                if s.metrics.task_count >= self.min_tasks
            ]

            if sibling_fitnesses:
                best_sibling_fitness = max(sibling_fitnesses)
                gap = best_sibling_fitness - node_fitness

                if gap > self.fitness_gap_threshold:
                    return PruningDecision(
                        should_prune=True,
                        confidence=0.7,
                        criteria=[PruningCriterion.REDUNDANT],
                        reason=f"Sibling fitness {best_sibling_fitness:.2f} >> node {node_fitness:.2f}",
                        expected_impact=0.03
                    )

        return PruningDecision(
            should_prune=False,
            confidence=0.0,
            criteria=[],
            reason="Not redundant",
            expected_impact=0.0
        )


# ============================================================================
# Resource-Based Pruning
# ============================================================================

class ResourcePruningStrategy(PruningStrategy):
    """Prune resource-heavy nodes with poor ROI"""

    def __init__(
        self,
        max_avg_tokens: int = 10000,
        max_avg_time: float = 30.0,
        min_tasks: int = 3
    ):
        self.max_avg_tokens = max_avg_tokens
        self.max_avg_time = max_avg_time
        self.min_tasks = min_tasks

    def evaluate(
        self,
        node: Any,
        _parent: Any | None,
        _siblings: list[Any],
        _context: dict[str, Any]
    ) -> PruningDecision:

        if node.metrics.task_count < self.min_tasks:
            return PruningDecision(
                should_prune=False,
                confidence=0.0,
                criteria=[],
                reason="Insufficient task history",
                expected_impact=0.0
            )

        avg_tokens = node.metrics.avg_tokens
        avg_time = node.metrics.avg_time
        fitness = node.metrics.fitness_score()

        # High resource usage + low fitness = prune
        is_resource_heavy = (
            avg_tokens > self.max_avg_tokens or
            avg_time > self.max_avg_time
        )

        if is_resource_heavy and fitness < 0.5:
            return PruningDecision(
                should_prune=True,
                confidence=0.85,
                criteria=[PruningCriterion.RESOURCE_HEAVY],
                reason=f"High resources (tokens={avg_tokens:.0f}, time={avg_time:.1f}s) + low fitness {fitness:.2f}",
                expected_impact=0.15  # Good savings
            )

        return PruningDecision(
            should_prune=False,
            confidence=0.0,
            criteria=[],
            reason="Resource usage acceptable",
            expected_impact=0.0
        )


# ============================================================================
# Composite Pruning Strategy
# ============================================================================

class CompositePruningStrategy(PruningStrategy):
    """Combines multiple pruning strategies"""

    def __init__(
        self,
        strategies: list[PruningStrategy] | None = None,
        min_confidence: float = 0.7
    ):
        self.strategies = strategies or [
            FitnessPruningStrategy(),
            RedundancyPruningStrategy(),
            ResourcePruningStrategy()
        ]
        self.min_confidence = min_confidence

    def evaluate(
        self,
        node: Any,
        parent: Any | None,
        siblings: list[Any],
        context: dict[str, Any]
    ) -> PruningDecision:

        decisions = [
            strategy.evaluate(node, parent, siblings, context)
            for strategy in self.strategies
        ]

        # Aggregate decisions
        should_prune_votes = sum(1 for d in decisions if d.should_prune)
        total_confidence = sum(d.confidence for d in decisions if d.should_prune)
        all_criteria = []
        all_reasons = []

        for d in decisions:
            if d.should_prune:
                all_criteria.extend(d.criteria)
                all_reasons.append(d.reason)

        # Decision: majority vote + high confidence
        if should_prune_votes > len(self.strategies) / 2:
            avg_confidence = total_confidence / should_prune_votes if should_prune_votes > 0 else 0

            if avg_confidence >= self.min_confidence:
                return PruningDecision(
                    should_prune=True,
                    confidence=avg_confidence,
                    criteria=list(set(all_criteria)),
                    reason="; ".join(all_reasons),
                    expected_impact=max(d.expected_impact for d in decisions)
                )

        return PruningDecision(
            should_prune=False,
            confidence=0.0,
            criteria=[],
            reason="No strong pruning signal",
            expected_impact=0.0
        )


# ============================================================================
# Smart Pruner
# ============================================================================

class SmartPruner:
    """
    Intelligent pruner with multiple strategies and safety checks
    """

    def __init__(
        self,
        strategy: PruningStrategy | None = None,
        dry_run: bool = False,
        preserve_min_nodes: int = 1
    ):
        """
        Initialize smart pruner

        Args:
            strategy: Pruning strategy (default: composite)
            dry_run: If True, only evaluate without pruning
            preserve_min_nodes: Minimum nodes to keep in structure
        """
        self.strategy = strategy or CompositePruningStrategy()
        self.dry_run = dry_run
        self.preserve_min_nodes = preserve_min_nodes

        # Tracking
        self.pruned_nodes: list[str] = []
        self.evaluation_cache: dict[str, PruningDecision] = {}

    def prune_structure(
        self,
        root: Any,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Prune structure using intelligent strategy

        Args:
            root: Root node
            context: Additional context

        Returns:
            Pruning report
        """
        context = context or {}
        self.pruned_nodes.clear()
        self.evaluation_cache.clear()

        total_nodes_before = self._count_nodes(root)
        fitness_before = root.metrics.fitness_score() if root.metrics.task_count > 0 else 0.0

        # Collect pruning candidates
        candidates = self._identify_candidates(root, context)

        # Sort by expected impact (highest first)
        candidates.sort(key=lambda x: x[2].expected_impact, reverse=True)

        # Prune candidates
        for node, parent, decision in candidates:
            # Safety check: don't prune too many
            current_nodes = self._count_nodes(root)
            if current_nodes <= self.preserve_min_nodes:
                logger.warning(f"Stopping pruning: at minimum node count {self.preserve_min_nodes}")
                break

            if not self.dry_run:
                # Actually remove node
                parent.children.remove(node)

            self.pruned_nodes.append(node.node_id)
            logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}Pruned {node.node_id}: {decision.reason}")

        total_nodes_after = self._count_nodes(root)
        fitness_after = root.metrics.fitness_score() if root.metrics.task_count > 0 else 0.0

        return {
            'pruned_count': len(self.pruned_nodes),
            'pruned_nodes': self.pruned_nodes,
            'nodes_before': total_nodes_before,
            'nodes_after': total_nodes_after,
            'fitness_before': fitness_before,
            'fitness_after': fitness_after,
            'fitness_improvement': fitness_after - fitness_before,
            'dry_run': self.dry_run
        }

    def _identify_candidates(
        self,
        root: Any,
        context: dict[str, Any]
    ) -> list[tuple[Any, Any, PruningDecision]]:
        """Identify pruning candidates"""
        candidates = []

        def _evaluate_node(node: Any, parent: Any | None = None):
            # Get siblings
            siblings = []
            if parent:
                siblings = [c for c in parent.children if c != node]

            # Recurse to children first
            for child in node.children[:]:
                _evaluate_node(child, node)

            # Evaluate this node (skip root)
            if parent is not None:
                decision = self.strategy.evaluate(node, parent, siblings, context)
                self.evaluation_cache[node.node_id] = decision

                if decision.should_prune:
                    candidates.append((node, parent, decision))

        _evaluate_node(root)

        return candidates

    def get_evaluation(self, node_id: str) -> PruningDecision | None:
        """Get cached evaluation for a node"""
        return self.evaluation_cache.get(node_id)

    def get_all_evaluations(self) -> dict[str, PruningDecision]:
        """Get all evaluations"""
        return self.evaluation_cache.copy()

    def _count_nodes(self, node: Any) -> int:
        """Count nodes in tree"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count
