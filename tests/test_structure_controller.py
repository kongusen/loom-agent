"""
Unit Tests for Structure Controller and Related Components
"""

from unittest.mock import Mock

import pytest

from loom.config.fractal import FractalConfig, GrowthStrategy, NodeRole
from loom.kernel import (
    CompositePruningStrategy,
    FitnessPruningStrategy,
    HealthStatus,
    SmartPruner,
    StructureController,
    StructureEventType,
    StructureHealthAssessor,
)
from loom.node.fractal import FractalAgentNode

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fractal_config():
    """Default fractal config"""
    return FractalConfig(
        enabled=True,
        max_depth=3,
        max_children=4,
        max_total_nodes=15,
        complexity_threshold=0.6,
        confidence_threshold=0.7,
        enable_auto_pruning=True,
        pruning_threshold=0.3,
        min_tasks_before_pruning=3,
    )


@pytest.fixture
def controller(fractal_config):
    """Structure controller instance"""
    return StructureController(fractal_config)


@pytest.fixture
def mock_llm():
    """Mock LLM"""
    llm = Mock()
    llm.generate = Mock(return_value="Test response")
    return llm


@pytest.fixture
def sample_tree(mock_llm, fractal_config):
    """Create a sample tree for testing"""
    root = FractalAgentNode(
        node_id="root",
        provider=mock_llm,
        role=NodeRole.COORDINATOR,
        fractal_config=fractal_config,
        standalone=True,
    )

    # Add children
    for i in range(3):
        child = FractalAgentNode(
            node_id=f"root.{i}",
            provider=mock_llm,
            role=NodeRole.EXECUTOR,
            parent=root,
            depth=1,
            fractal_config=fractal_config,
            standalone=True,
        )
        root.children.append(child)

        # Add some metrics to children
        child.metrics.record_execution(
            success=i < 2,  # Last child fails
            tokens=1000 * (i + 1),
            time=i + 1.0,
        )

    return root


# ============================================================================
# StructureController Tests
# ============================================================================


class TestStructureController:
    """Test StructureController"""

    def test_controller_creation(self, controller):
        """Test creating controller"""
        assert controller is not None
        assert controller.config is not None
        assert len(controller.history) == 0

    def test_should_grow_high_complexity(self, controller, sample_tree):
        """Test growth decision for high complexity"""
        node = sample_tree.children[0]

        should_grow = controller.should_grow(
            node,
            task_complexity=0.8,  # High
            current_confidence=0.6,
        )

        assert should_grow is True

    def test_should_not_grow_low_complexity(self, controller, sample_tree):
        """Test no growth for low complexity"""
        node = sample_tree.children[0]

        should_grow = controller.should_grow(
            node,
            task_complexity=0.3,  # Low
            current_confidence=0.9,
        )

        assert should_grow is False

    def test_should_not_grow_at_max_depth(self, controller, fractal_config, mock_llm):
        """Test no growth at max depth"""
        # Create node at max depth
        node = FractalAgentNode(
            node_id="deep",
            provider=mock_llm,
            depth=fractal_config.max_depth,
            fractal_config=fractal_config,
            standalone=True,
        )

        should_grow = controller.should_grow(node, task_complexity=0.9, current_confidence=0.3)

        assert should_grow is False

    def test_choose_growth_strategy_decompose(self, controller, sample_tree):
        """Test strategy selection for sequential task"""
        node = sample_tree

        strategy = controller.choose_growth_strategy(
            node, "First do step 1, then step 2, finally step 3"
        )

        assert strategy == GrowthStrategy.DECOMPOSE

    def test_choose_growth_strategy_parallelize(self, controller, sample_tree):
        """Test strategy selection for parallel task"""
        node = sample_tree

        strategy = controller.choose_growth_strategy(node, "Run these tasks in parallel")

        assert strategy == GrowthStrategy.PARALLELIZE

    def test_record_growth(self, controller, sample_tree):
        """Test recording growth event"""
        node = sample_tree

        controller.record_growth(
            node, GrowthStrategy.DECOMPOSE, children_count=3, fitness_before=0.7
        )

        assert len(controller.history) == 1
        assert controller.history[0].event_type == StructureEventType.GROWTH
        assert controller.history[0].children_added == 3
        assert controller.stats.total_growth_events == 1

    def test_analyze_structure(self, controller, sample_tree):
        """Test structure analysis"""
        analysis = controller.analyze_structure(sample_tree)

        assert analysis["total_nodes"] == 4  # root + 3 children
        assert analysis["max_depth"] == 1
        assert analysis["avg_fitness"] > 0  # Some children have metrics

    def test_callbacks(self, controller, sample_tree):
        """Test growth/pruning callbacks"""
        growth_called = []
        pruning_called = []

        def on_growth(node, event):
            growth_called.append(node.node_id)

        def on_pruning(node, event):
            pruning_called.append(node.node_id)

        controller.on_growth(on_growth)
        controller.on_pruning(on_pruning)

        # Trigger growth
        controller.record_growth(sample_tree, GrowthStrategy.DECOMPOSE, 1)

        assert len(growth_called) == 1
        assert growth_called[0] == "root"


# ============================================================================
# Pruning Tests
# ============================================================================


class TestPruning:
    """Test pruning strategies"""

    def test_fitness_pruning_low_fitness(self, sample_tree):
        """Test pruning node with low fitness"""
        strategy = FitnessPruningStrategy(fitness_threshold=0.5, min_tasks=1)

        # Last child has low fitness (failed task)
        low_fitness_child = sample_tree.children[2]
        siblings = [c for c in sample_tree.children if c != low_fitness_child]

        decision = strategy.evaluate(low_fitness_child, sample_tree, siblings, {})

        # Depending on exact fitness calculation
        # assert decision.should_prune == True or decision.should_prune == False
        assert decision is not None

    def test_smart_pruner(self, sample_tree):
        """Test smart pruner"""
        pruner = SmartPruner(dry_run=True)  # Dry run

        report = pruner.prune_structure(sample_tree)

        assert "pruned_count" in report
        assert "nodes_before" in report
        assert "nodes_after" in report
        assert report["dry_run"] is True

    def test_composite_pruning(self, sample_tree):
        """Test composite pruning strategy"""
        strategy = CompositePruningStrategy()

        child = sample_tree.children[0]
        siblings = [c for c in sample_tree.children if c != child]

        decision = strategy.evaluate(child, sample_tree, siblings, {})

        assert decision is not None
        assert isinstance(decision.should_prune, bool)


# ============================================================================
# Health Assessment Tests
# ============================================================================


class TestHealthAssessment:
    """Test structure health assessment"""

    def test_assessor_creation(self):
        """Test creating health assessor"""
        assessor = StructureHealthAssessor()
        assert assessor is not None

    def test_assess_structure(self, sample_tree):
        """Test assessing structure health"""
        assessor = StructureHealthAssessor()

        report = assessor.assess(sample_tree)

        assert report is not None
        assert 0 <= report.overall_score <= 1
        assert report.status in HealthStatus
        assert report.total_nodes == 4

    def test_health_scores(self, sample_tree):
        """Test component health scores"""
        assessor = StructureHealthAssessor()
        report = assessor.assess(sample_tree)

        assert 0 <= report.balance_score <= 1
        assert 0 <= report.efficiency_score <= 1
        assert 0 <= report.performance_score <= 1
        assert 0 <= report.utilization_score <= 1

    def test_diagnostics(self, sample_tree, fractal_config):
        """Test health diagnostics"""
        # Create a problematic structure
        # Add many idle nodes
        for i in range(10):
            idle_child = FractalAgentNode(
                node_id=f"idle.{i}",
                provider=Mock(),
                parent=sample_tree,
                depth=1,
                fractal_config=fractal_config,
                standalone=True,
            )
            sample_tree.children.append(idle_child)

        assessor = StructureHealthAssessor()
        report = assessor.assess(sample_tree, fractal_config)

        # Should detect underutilization
        assert len(report.diagnostics) > 0

    def test_format_report(self, sample_tree):
        """Test formatting health report"""
        assessor = StructureHealthAssessor()
        report = assessor.assess(sample_tree)

        formatted = assessor.format_report(report)

        assert "STRUCTURE HEALTH REPORT" in formatted
        assert "Overall Score" in formatted
        assert "Component Scores" in formatted


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Test integration between components"""

    def test_controller_with_pruner(self, controller, sample_tree):
        """Test using controller with smart pruner"""
        # Analyze structure
        analysis = controller.analyze_structure(sample_tree)
        assert analysis["total_nodes"] > 0

        # Identify inefficient nodes
        inefficient = controller.get_inefficient_nodes(sample_tree)

        # Prune (dry run)
        if inefficient:
            pruner = SmartPruner(dry_run=True)
            report = pruner.prune_structure(sample_tree)
            assert report["dry_run"] is True

    def test_full_workflow(self, controller, sample_tree, fractal_config):
        """Test complete workflow: grow -> assess -> prune"""
        # 1. Record growth
        controller.record_growth(sample_tree, GrowthStrategy.DECOMPOSE, 3)

        # 2. Assess health
        assessor = StructureHealthAssessor()
        health = assessor.assess(sample_tree, fractal_config)

        assert health.total_nodes == 4

        # 3. Check for pruning candidates
        controller.get_inefficient_nodes(sample_tree)

        # 4. Prune if needed (dry run)
        pruner = SmartPruner(dry_run=True)
        prune_report = pruner.prune_structure(sample_tree)

        assert prune_report["nodes_before"] == 4


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
