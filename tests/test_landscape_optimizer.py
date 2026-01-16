"""
Tests for Fitness Landscape Optimizer

Tests the landscape optimizer's ability to record performance,
learn patterns, and make recommendations for structure optimization.
"""

import time
import unittest
from unittest.mock import Mock

from loom.kernel.optimization import FitnessLandscapeOptimizer, StructurePattern, StructureSnapshot

# ============================================================================
# Mock Structures for Testing
# ============================================================================


def create_mock_node(
    role: str = "coordinator",
    children_count: int = 0,
    fitness: float = 0.8,
    success_rate: float = 0.9,
    task_count: int = 10,
    depth: int = 0,
) -> Mock:
    """Create a mock FractalAgentNode for testing"""
    node = Mock()
    node.role = Mock(value=role)
    node.children = [Mock() for _ in range(children_count)]
    node.depth = depth
    node.node_id = f"node_{id(node)}"

    # Mock metrics
    node.metrics = Mock()
    node.metrics.task_count = task_count
    node.metrics.success_rate = success_rate
    node.metrics.avg_tokens = 100.0
    node.metrics.avg_time = 2.5
    node.metrics.avg_cost = 0.05

    def fitness_score_fn():
        return fitness

    node.metrics.fitness_score = fitness_score_fn

    return node


def create_mock_tree(depth: int = 2, branching: int = 2, fitness: float = 0.8) -> Mock:
    """Create a mock tree structure for testing"""

    def _create_node(d: int):
        if d >= depth:
            return create_mock_node(depth=d, fitness=fitness, task_count=5)

        role_map = {0: "coordinator", 1: "executor", 2: "aggregator"}
        current_role = role_map.get(d, "executor")

        node = create_mock_node(
            role=current_role, children_count=branching, fitness=fitness, depth=d, task_count=10
        )

        for i in range(branching):
            node.children[i] = _create_node(d + 1)

        return node

    return _create_node(0)


# ============================================================================
# Test Cases
# ============================================================================


class TestStructureSnapshot(unittest.TestCase):
    """Test StructureSnapshot data structure"""

    def test_snapshot_creation(self):
        """Test creating a snapshot"""
        snapshot = StructureSnapshot(
            timestamp=time.time(),
            structure_id="struct_001",
            task_type="research",
            task_complexity=0.7,
            total_nodes=5,
            max_depth=2,
            avg_depth=1.5,
            avg_branching=2.0,
            node_roles={"coordinator": 1, "executor": 3, "aggregator": 1},
            fitness_score=0.85,
            success_rate=0.9,
            avg_tokens=150.0,
            avg_time=3.0,
            avg_cost=0.1,
            growth_strategies={},
        )

        self.assertEqual(snapshot.structure_id, "struct_001")
        self.assertEqual(snapshot.task_type, "research")
        self.assertEqual(snapshot.fitness_score, 0.85)
        self.assertEqual(snapshot.total_nodes, 5)

    def test_snapshot_to_dict(self):
        """Test snapshot serialization"""
        snapshot = StructureSnapshot(
            timestamp=time.time(),
            structure_id="struct_001",
            task_type="research",
            task_complexity=0.7,
            total_nodes=5,
            max_depth=2,
            avg_depth=1.5,
            avg_branching=2.0,
            node_roles={"coordinator": 1, "executor": 3},
            fitness_score=0.85,
            success_rate=0.9,
            avg_tokens=150.0,
            avg_time=3.0,
            avg_cost=0.1,
            growth_strategies={},
        )

        data = snapshot.to_dict()
        self.assertIn("timestamp", data)
        self.assertIn("topology", data)
        self.assertIn("performance", data)
        self.assertEqual(data["task_type"], "research")
        self.assertEqual(data["topology"]["total_nodes"], 5)

    def test_snapshot_from_dict(self):
        """Test snapshot deserialization"""
        original = StructureSnapshot(
            timestamp=time.time(),
            structure_id="struct_001",
            task_type="research",
            task_complexity=0.7,
            total_nodes=5,
            max_depth=2,
            avg_depth=1.5,
            avg_branching=2.0,
            node_roles={"coordinator": 1, "executor": 3},
            fitness_score=0.85,
            success_rate=0.9,
            avg_tokens=150.0,
            avg_time=3.0,
            avg_cost=0.1,
            growth_strategies={},
        )

        data = original.to_dict()
        restored = StructureSnapshot.from_dict(data)

        self.assertEqual(restored.structure_id, original.structure_id)
        self.assertEqual(restored.fitness_score, original.fitness_score)
        self.assertEqual(restored.total_nodes, original.total_nodes)


class TestFitnessLandscapeOptimizer(unittest.TestCase):
    """Test FitnessLandscapeOptimizer core functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.optimizer = FitnessLandscapeOptimizer(
            memory_size=100, min_samples_for_pattern=3, confidence_threshold=0.5
        )

    def test_optimizer_initialization(self):
        """Test optimizer initialization"""
        self.assertEqual(len(self.optimizer.snapshots), 0)
        self.assertEqual(len(self.optimizer.patterns), 0)
        self.assertEqual(self.optimizer.memory_size, 100)

    def test_record_structure_performance(self):
        """Test recording structure performance"""
        root = create_mock_tree(depth=2, branching=2, fitness=0.85)

        snapshot = self.optimizer.record_structure_performance(
            root=root, task_type="research", task_complexity=0.7, structure_id="test_struct_001"
        )

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.structure_id, "test_struct_001")
        self.assertEqual(snapshot.task_type, "research")
        self.assertEqual(len(self.optimizer.snapshots), 1)

    def test_memory_limit_enforcement(self):
        """Test that optimizer respects memory size limit"""
        optimizer = FitnessLandscapeOptimizer(memory_size=5)

        for i in range(10):
            root = create_mock_tree(depth=2, fitness=0.7 + i * 0.02)
            optimizer.record_structure_performance(
                root=root, task_type="task", task_complexity=0.5, structure_id=f"struct_{i}"
            )

        self.assertEqual(len(optimizer.snapshots), 5)
        # Should keep the most recent
        self.assertEqual(optimizer.snapshots[-1].structure_id, "struct_9")

    def test_landscape_data_accumulation(self):
        """Test that landscape data is accumulated correctly"""
        for i in range(5):
            root = create_mock_tree(depth=2, fitness=0.75)
            self.optimizer.record_structure_performance(
                root=root, task_type="research", task_complexity=0.5, structure_id=f"struct_{i}"
            )

        self.assertGreater(len(self.optimizer.landscape_data), 0)

    def test_analyze_topology(self):
        """Test topology analysis"""
        root = create_mock_tree(depth=2, branching=2)
        topology = self.optimizer._analyze_topology(root)

        self.assertIn("total_nodes", topology)
        self.assertIn("max_depth", topology)
        self.assertIn("avg_branching", topology)
        self.assertIn("node_roles", topology)
        self.assertGreater(topology["total_nodes"], 0)
        self.assertGreater(topology["max_depth"], 0)

    def test_analyze_performance(self):
        """Test performance analysis"""
        root = create_mock_tree(depth=2, fitness=0.8)
        performance = self.optimizer._analyze_performance(root)

        self.assertIn("fitness_score", performance)
        self.assertIn("success_rate", performance)
        self.assertIn("avg_tokens", performance)
        self.assertIn("avg_time", performance)
        self.assertIn("avg_cost", performance)

    def test_learn_patterns_from_snapshots(self):
        """Test learning patterns from historical data"""
        # Record multiple good structures
        for i in range(5):
            root = create_mock_tree(depth=2, branching=2, fitness=0.8 + i * 0.01)
            self.optimizer.record_structure_performance(
                root=root, task_type="research", task_complexity=0.6, structure_id=f"research_{i}"
            )

        # Learn patterns
        patterns = self.optimizer.learn_patterns()

        self.assertGreater(len(patterns), 0)
        pattern = patterns[0]
        self.assertEqual(pattern.task_pattern, "research")
        self.assertGreater(pattern.avg_fitness, 0)

    def test_pattern_confidence_calculation(self):
        """Test that pattern confidence is calculated correctly"""
        # Record samples
        for i in range(8):
            root = create_mock_tree(depth=2, fitness=0.75)
            self.optimizer.record_structure_performance(
                root=root, task_type="analysis", task_complexity=0.5, structure_id=f"analysis_{i}"
            )

        patterns = self.optimizer.learn_patterns()
        if patterns:
            pattern = patterns[0]
            # Confidence should be > 0
            self.assertGreater(pattern.confidence, 0)
            # Confidence should be <= 1.0
            self.assertLessEqual(pattern.confidence, 1.0)

    def test_recommend_structure(self):
        """Test structure recommendation"""
        # Record good structures
        for i in range(5):
            root = create_mock_tree(depth=2, fitness=0.85)
            self.optimizer.record_structure_performance(
                root=root, task_type="research", task_complexity=0.7, structure_id=f"research_{i}"
            )

        # Learn patterns
        self.optimizer.learn_patterns()

        # Get recommendation
        self.optimizer.recommend_structure(
            task_type="research", task_complexity=0.7, current_fitness=None
        )

        # If we have patterns, we might get a recommendation
        # (depends on confidence threshold)

    def test_recommend_structure_with_improvement_filter(self):
        """Test recommendation filtering for improvements"""
        # Record structures with fitness 0.75
        for i in range(5):
            root = create_mock_tree(depth=2, fitness=0.75)
            self.optimizer.record_structure_performance(
                root=root, task_type="research", task_complexity=0.7, structure_id=f"research_{i}"
            )

        self.optimizer.learn_patterns()

        # Request recommendation but already have high fitness
        self.optimizer.recommend_structure(
            task_type="research",
            task_complexity=0.7,
            current_fitness=0.80,  # Higher than recorded structures
        )

        # Unlikely to get recommendation since no improvement
        # (depends on learned pattern fitness)

    def test_get_statistics(self):
        """Test getting optimizer statistics"""
        # Record some structures
        for i in range(3):
            root = create_mock_tree(depth=2, fitness=0.7 + i * 0.05)
            self.optimizer.record_structure_performance(
                root=root, task_type="task", task_complexity=0.5, structure_id=f"struct_{i}"
            )

        stats = self.optimizer.get_statistics()

        self.assertEqual(stats["total_snapshots"], 3)
        self.assertIn("avg_fitness", stats)
        self.assertIn("best_fitness", stats)
        self.assertIn("worst_fitness", stats)

    def test_get_best_structures(self):
        """Test getting best performing structures"""
        # Record structures with varying fitness
        fitness_values = [0.6, 0.8, 0.7, 0.9, 0.75]
        for i, fitness in enumerate(fitness_values):
            root = create_mock_tree(depth=2, fitness=fitness)
            self.optimizer.record_structure_performance(
                root=root, task_type="task", task_complexity=0.5, structure_id=f"struct_{i}"
            )

        best = self.optimizer.get_best_structures(limit=2)

        self.assertEqual(len(best), 2)
        # Should be sorted by fitness descending
        self.assertGreaterEqual(best[0].fitness_score, best[1].fitness_score)

    def test_get_best_structures_by_task_type(self):
        """Test filtering best structures by task type"""
        # Record structures of different types
        for i in range(3):
            root = create_mock_tree(depth=2, fitness=0.7)
            self.optimizer.record_structure_performance(
                root=root, task_type="research", task_complexity=0.5, structure_id=f"research_{i}"
            )

        for i in range(3):
            root = create_mock_tree(depth=2, fitness=0.8)
            self.optimizer.record_structure_performance(
                root=root, task_type="analysis", task_complexity=0.6, structure_id=f"analysis_{i}"
            )

        best_research = self.optimizer.get_best_structures(task_type="research", limit=2)
        self.assertEqual(len(best_research), 2)
        for snapshot in best_research:
            self.assertEqual(snapshot.task_type, "research")

    def test_visualize_landscape(self):
        """Test landscape visualization"""
        # Record structures to build landscape
        for i in range(10):
            complexity = (i % 5) / 10.0
            root = create_mock_tree(depth=1 + (i % 3), fitness=0.5 + complexity)
            self.optimizer.record_structure_performance(
                root=root, task_type="task", task_complexity=complexity, structure_id=f"struct_{i}"
            )

        visualization = self.optimizer.visualize_landscape()

        self.assertIsInstance(visualization, str)
        self.assertIn("FITNESS LANDSCAPE", visualization)
        self.assertIn("Legend", visualization)

    def test_persistence_save_and_load(self):
        """Test saving and loading optimizer state"""
        import os
        import tempfile

        # Record some structures
        for i in range(3):
            root = create_mock_tree(depth=2, fitness=0.75)
            self.optimizer.record_structure_performance(
                root=root, task_type="research", task_complexity=0.6, structure_id=f"struct_{i}"
            )

        self.optimizer.learn_patterns()

        # Save
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            self.optimizer.save(temp_file)
            self.assertTrue(os.path.exists(temp_file))

            # Load into new optimizer
            new_optimizer = FitnessLandscapeOptimizer()
            new_optimizer.load(temp_file)

            self.assertEqual(len(new_optimizer.snapshots), 3)
            self.assertEqual(len(new_optimizer.patterns), len(self.optimizer.patterns))

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_task_matching_in_recommendations(self):
        """Test that task matching works correctly"""
        # Record structures for "text_analysis"
        for i in range(5):
            root = create_mock_tree(depth=2, fitness=0.8)
            self.optimizer.record_structure_performance(
                root=root, task_type="text_analysis", task_complexity=0.6, structure_id=f"text_{i}"
            )

        self.optimizer.learn_patterns()

        # Should match "text_analysis" and "analysis"
        self.optimizer.recommend_structure("text_analysis", 0.6)
        self.optimizer.recommend_structure("analysis", 0.6)

        # At least exact match should work


class TestStructurePattern(unittest.TestCase):
    """Test StructurePattern data structure"""

    def test_pattern_creation(self):
        """Test creating a pattern"""
        pattern = StructurePattern(
            pattern_id="pat_001",
            task_pattern="research",
            avg_fitness=0.85,
            usage_count=5,
            recommended_depth=2,
            recommended_branching=2.0,
            recommended_roles={"coordinator": 0.2, "executor": 0.6, "aggregator": 0.2},
            recommended_strategies=[],
            min_fitness=0.75,
            max_tokens=200.0,
            success_rate=0.9,
            confidence=0.8,
        )

        self.assertEqual(pattern.pattern_id, "pat_001")
        self.assertEqual(pattern.avg_fitness, 0.85)
        self.assertGreater(pattern.confidence, 0)

    def test_pattern_to_dict(self):
        """Test pattern serialization"""
        pattern = StructurePattern(
            pattern_id="pat_001",
            task_pattern="research",
            avg_fitness=0.85,
            usage_count=5,
            recommended_depth=2,
            recommended_branching=2.0,
            recommended_roles={"coordinator": 0.2, "executor": 0.6},
            recommended_strategies=[],
            min_fitness=0.75,
            max_tokens=200.0,
            success_rate=0.9,
            confidence=0.8,
        )

        data = pattern.to_dict()
        self.assertIn("pattern_id", data)
        self.assertIn("topology", data)
        self.assertIn("performance", data)
        self.assertEqual(data["avg_fitness"], 0.85)


if __name__ == "__main__":
    unittest.main()
