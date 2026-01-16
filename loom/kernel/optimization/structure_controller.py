"""
Structure Controller - Manages fractal node structure growth and pruning

This module provides intelligent control over node structure evolution,
including growth decisions, pruning strategies, and structure optimization.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from loom.config.fractal import FractalConfig, GrowthStrategy, NodeRole

logger = logging.getLogger(__name__)


# ============================================================================
# Events and History
# ============================================================================

class StructureEventType(Enum):
    """Types of structure events"""
    GROWTH = "growth"           # Node growth/spawning
    PRUNING = "pruning"         # Node removal
    OPTIMIZATION = "optimization"  # Structure optimization
    REBALANCE = "rebalance"     # Load rebalancing


@dataclass
class StructureEvent:
    """Record of a structure change event"""
    timestamp: float
    event_type: StructureEventType
    node_id: str
    details: dict[str, Any]

    # Growth-specific
    strategy: GrowthStrategy | None = None
    children_added: int = 0

    # Pruning-specific
    nodes_removed: int = 0
    pruning_reason: str | None = None

    # Performance impact
    before_fitness: float = 0.0
    after_fitness: float = 0.0


@dataclass
class StructureStats:
    """Statistics about structure evolution"""
    total_nodes: int = 0
    total_growth_events: int = 0
    total_pruning_events: int = 0
    total_nodes_pruned: int = 0
    avg_depth: float = 0.0
    max_depth: int = 0
    avg_branching_factor: float = 0.0

    # Performance stats
    avg_fitness: float = 0.0
    min_fitness: float = 1.0
    max_fitness: float = 0.0

    # Time stats
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0


# ============================================================================
# Structure Controller
# ============================================================================

class StructureController:
    """
    Controls fractal node structure growth, pruning, and optimization

    Responsibilities:
    - Decide when to grow structure
    - Choose optimal growth strategies
    - Prune inefficient nodes
    - Track structure evolution
    - Optimize structure performance
    """

    def __init__(
        self,
        config: FractalConfig,
        enable_history: bool = True,
        max_history_size: int = 1000
    ):
        """
        Initialize structure controller

        Args:
            config: Fractal configuration
            enable_history: Whether to track structure history
            max_history_size: Maximum history events to keep
        """
        self.config = config
        self.enable_history = enable_history
        self.max_history_size = max_history_size

        # Event history
        self.history: list[StructureEvent] = []

        # Statistics
        self.stats = StructureStats()

        # Callbacks
        self._growth_callbacks: list[Callable] = []
        self._pruning_callbacks: list[Callable] = []

    # ========================================================================
    # Growth Control
    # ========================================================================

    def should_grow(
        self,
        node: Any,  # FractalAgentNode
        task_complexity: float,
        current_confidence: float = 0.5
    ) -> bool:
        """
        Determine if node should spawn children

        Args:
            node: The node being evaluated
            task_complexity: Estimated task complexity (0-1)
            current_confidence: Current confidence in handling task (0-1)

        Returns:
            True if node should grow
        """
        # Check if auto-growth is enabled (default to True if not set)
        enable_growth = getattr(self.config, 'enable_auto_growth', True)
        if not enable_growth:
            return False

        # Condition 1: Complexity threshold
        if task_complexity < self.config.complexity_threshold:
            logger.debug(f"Node {node.node_id}: Complexity {task_complexity:.2f} below threshold {self.config.complexity_threshold}")
            return False

        # Condition 2: Depth limit
        if node.depth >= self.config.max_depth:
            logger.debug(f"Node {node.node_id}: At max depth {self.config.max_depth}")
            return False

        # Condition 3: Children limit
        if len(node.children) >= self.config.max_children:
            logger.debug(f"Node {node.node_id}: At max children {self.config.max_children}")
            return False

        # Condition 4: Total nodes limit
        total_nodes = self._count_total_nodes(node)
        if total_nodes >= self.config.max_total_nodes:
            logger.debug(f"Structure: At max total nodes {self.config.max_total_nodes}")
            return False

        # Condition 5: Low confidence (need help)
        if current_confidence < self.config.confidence_threshold:
            logger.info(f"Node {node.node_id}: Low confidence {current_confidence:.2f}, should grow")
            return True

        # Condition 6: High complexity (even with good confidence)
        if task_complexity > 0.8:
            logger.info(f"Node {node.node_id}: High complexity {task_complexity:.2f}, should grow")
            return True

        # Condition 7: Historical performance (if node has track record)
        if node.metrics.task_count > 3:
            fitness = node.metrics.fitness_score()
            if fitness < 0.5:  # Poor performance
                logger.info(f"Node {node.node_id}: Low fitness {fitness:.2f}, should grow for help")
                return True

        return False

    def choose_growth_strategy(
        self,
        node: Any,
        task: str,
        task_features: dict[str, Any] | None = None
    ) -> GrowthStrategy:
        """
        Choose optimal growth strategy based on task characteristics

        Args:
            node: The node that will grow
            task: Task description
            task_features: Optional extracted task features

        Returns:
            Recommended GrowthStrategy
        """
        if task_features is None:
            task_features = self._analyze_task(task)

        # Strategy 1: Detect sequential patterns
        if task_features.get('has_sequence', False):
            return GrowthStrategy.DECOMPOSE

        # Strategy 2: Detect parallel opportunities
        if task_features.get('has_parallel', False):
            return GrowthStrategy.PARALLELIZE

        # Strategy 3: Detect specialization needs
        if task_features.get('has_domains', False):
            return GrowthStrategy.SPECIALIZE

        # Strategy 4: Detect iterative needs
        if task_features.get('has_iteration', False):
            return GrowthStrategy.ITERATE

        # Strategy 5: Based on node role
        if node.role == NodeRole.COORDINATOR:
            # Coordinators typically decompose or parallelize
            return GrowthStrategy.DECOMPOSE
        elif node.role == NodeRole.SPECIALIST:
            # Specialists might iterate or get more specialists
            return GrowthStrategy.ITERATE

        # Default: Use config default
        return self.config.default_strategy

    def _analyze_task(self, task: str) -> dict[str, Any]:
        """Analyze task to extract features for strategy selection"""
        task_lower = task.lower()

        # Sequential indicators
        sequence_keywords = ["step", "first", "then", "after", "finally", "sequence", "order", "phase"]
        has_sequence = any(kw in task_lower for kw in sequence_keywords)

        # Parallel indicators
        parallel_keywords = ["parallel", "concurrent", "simultaneous", "independent", "separately"]
        has_parallel = any(kw in task_lower for kw in parallel_keywords)

        # Domain/specialization indicators
        domain_keywords = ["expert", "specialist", "domain", "field", "area"]
        has_domains = any(kw in task_lower for kw in domain_keywords)

        # Iteration indicators
        iteration_keywords = ["iterate", "refine", "improve", "optimize", "enhance"]
        has_iteration = any(kw in task_lower for kw in iteration_keywords)

        return {
            'has_sequence': has_sequence,
            'has_parallel': has_parallel,
            'has_domains': has_domains,
            'has_iteration': has_iteration,
            'length': len(task),
            'word_count': len(task.split())
        }

    def record_growth(
        self,
        node: Any,
        strategy: GrowthStrategy,
        children_count: int,
        fitness_before: float = 0.0
    ):
        """Record a growth event"""
        event = StructureEvent(
            timestamp=time.time(),
            event_type=StructureEventType.GROWTH,
            node_id=node.node_id,
            details={
                'role': node.role,
                'depth': node.depth,
                'children_count': children_count
            },
            strategy=strategy,
            children_added=children_count,
            before_fitness=fitness_before
        )

        self._add_event(event)
        self.stats.total_growth_events += 1

        # Execute callbacks
        for callback in self._growth_callbacks:
            try:
                callback(node, event)
            except Exception as e:
                logger.error(f"Growth callback error: {e}")

    # ========================================================================
    # Pruning Control
    # ========================================================================

    def should_prune(
        self,
        node: Any,
        parent: Any | None = None
    ) -> tuple[bool, str | None]:
        """
        Determine if node should be pruned

        Args:
            node: The node being evaluated
            parent: Parent node (for context)

        Returns:
            (should_prune, reason)
        """
        # Don't prune root
        if parent is None:
            return False, None

        # Check if auto-pruning is enabled
        if not self.config.enable_auto_pruning:
            return False, None

        # Require minimum task count before pruning
        if node.metrics.task_count < self.config.min_tasks_before_pruning:
            return False, None

        # Criterion 1: Low fitness score
        fitness = node.metrics.fitness_score()
        if fitness < self.config.pruning_threshold:
            return True, f"Low fitness: {fitness:.2f} < {self.config.pruning_threshold}"

        # Criterion 2: High failure rate
        if node.metrics.success_rate < 0.3:
            return True, f"High failure rate: {1 - node.metrics.success_rate:.1%}"

        # Criterion 3: Redundant node (parent or sibling does better)
        if parent and parent.metrics.task_count > 0:
            parent_fitness = parent.metrics.fitness_score()
            if parent_fitness > fitness + 0.2:  # Parent significantly better
                return True, f"Redundant: parent fitness {parent_fitness:.2f} >> node fitness {fitness:.2f}"

        # Criterion 4: Idle node (no recent activity)
        # This would require timestamp tracking - skip for now

        return False, None

    def prune_inefficient_nodes(
        self,
        root: Any,
        dry_run: bool = False
    ) -> list[str]:
        """
        Recursively prune inefficient nodes from structure

        Args:
            root: Root node of structure
            dry_run: If True, only identify but don't remove

        Returns:
            List of pruned node IDs
        """
        pruned = []

        def _prune_recursive(node: Any, parent: Any | None = None):
            # Check children first (bottom-up pruning)
            for child in node.children[:]:  # Copy to avoid modification issues
                _prune_recursive(child, node)

            # Check if this node should be pruned
            if parent is not None:
                should_prune, reason = self.should_prune(node, parent)

                if should_prune:
                    pruned.append(node.node_id)

                    if not dry_run:
                        # Remove from parent
                        parent.children.remove(node)

                        # Record event
                        self.record_pruning(
                            node,
                            reason=reason or "No reason provided",
                            fitness_before=node.metrics.fitness_score()
                        )

                        logger.info(f"🪓 Pruned node {node.node_id}: {reason}")
                    else:
                        logger.info(f"🔍 Would prune {node.node_id}: {reason}")

        _prune_recursive(root)

        return pruned

    def record_pruning(
        self,
        node: Any,
        reason: str,
        fitness_before: float = 0.0
    ):
        """Record a pruning event"""
        event = StructureEvent(
            timestamp=time.time(),
            event_type=StructureEventType.PRUNING,
            node_id=node.node_id,
            details={
                'role': node.role,
                'depth': node.depth,
                'task_count': node.metrics.task_count
            },
            nodes_removed=1 + self._count_total_nodes(node) - 1,  # Include subtree
            pruning_reason=reason,
            before_fitness=fitness_before
        )

        self._add_event(event)
        self.stats.total_pruning_events += 1
        self.stats.total_nodes_pruned += event.nodes_removed

        # Execute callbacks
        for callback in self._pruning_callbacks:
            try:
                callback(node, event)
            except Exception as e:
                logger.error(f"Pruning callback error: {e}")

    # ========================================================================
    # Structure Analysis
    # ========================================================================

    def analyze_structure(self, root: Any) -> dict[str, Any]:
        """
        Analyze structure and compute statistics

        Args:
            root: Root node

        Returns:
            Dictionary with analysis results
        """
        nodes = []
        fitness_scores = []
        depths = []
        branching_factors = []

        def _collect_stats(node: Any, depth: int = 0):
            nodes.append(node)
            depths.append(depth)

            if node.metrics.task_count > 0:
                fitness_scores.append(node.metrics.fitness_score())

            if node.children:
                branching_factors.append(len(node.children))
                for child in node.children:
                    _collect_stats(child, depth + 1)

        _collect_stats(root)

        # Update stats
        self.stats.total_nodes = len(nodes)
        self.stats.avg_depth = sum(depths) / len(depths) if depths else 0
        self.stats.max_depth = max(depths) if depths else 0
        self.stats.avg_branching_factor = (
            sum(branching_factors) / len(branching_factors)
            if branching_factors else 0
        )

        if fitness_scores:
            self.stats.avg_fitness = sum(fitness_scores) / len(fitness_scores)
            self.stats.min_fitness = min(fitness_scores)
            self.stats.max_fitness = max(fitness_scores)

        return {
            'total_nodes': self.stats.total_nodes,
            'max_depth': self.stats.max_depth,
            'avg_depth': self.stats.avg_depth,
            'avg_branching_factor': self.stats.avg_branching_factor,
            'avg_fitness': self.stats.avg_fitness,
            'fitness_range': (self.stats.min_fitness, self.stats.max_fitness),
            'growth_events': self.stats.total_growth_events,
            'pruning_events': self.stats.total_pruning_events,
            'nodes_pruned': self.stats.total_nodes_pruned
        }

    def get_inefficient_nodes(self, root: Any) -> list[tuple[Any, float, str]]:
        """
        Identify inefficient nodes without pruning

        Returns:
            List of (node, fitness, reason) tuples
        """
        inefficient = []

        def _check_node(node: Any, parent: Any | None = None):
            for child in node.children:
                _check_node(child, node)

            if parent is not None:
                should_prune, reason = self.should_prune(node, parent)
                if should_prune:
                    fitness = node.metrics.fitness_score()
                    inefficient.append((node, fitness, reason or "Unknown reason"))

        _check_node(root)

        return inefficient

    # ========================================================================
    # Callbacks
    # ========================================================================

    def on_growth(self, callback: Callable):
        """Register callback for growth events"""
        self._growth_callbacks.append(callback)

    def on_pruning(self, callback: Callable):
        """Register callback for pruning events"""
        self._pruning_callbacks.append(callback)

    # ========================================================================
    # Utilities
    # ========================================================================

    def _count_total_nodes(self, node: Any) -> int:
        """Count total nodes in subtree"""
        count = 1
        for child in node.children:
            count += self._count_total_nodes(child)
        return count

    def _add_event(self, event: StructureEvent):
        """Add event to history"""
        if not self.enable_history:
            return

        self.history.append(event)

        # Trim history if needed
        if len(self.history) > self.max_history_size:
            self.history = self.history[-self.max_history_size:]

    def get_history(
        self,
        event_type: StructureEventType | None = None,
        limit: int = 100
    ) -> list[StructureEvent]:
        """Get structure event history"""
        events = self.history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def get_stats(self) -> StructureStats:
        """Get current structure statistics"""
        return self.stats

    def reset_stats(self):
        """Reset statistics"""
        self.stats = StructureStats()

    def clear_history(self):
        """Clear event history"""
        self.history.clear()
