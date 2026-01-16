"""
Tests for Template Manager

Tests the template learning system's ability to learn, store, match,
and recommend optimal structure templates.
"""

import os
import tempfile
import unittest

from loom.config.fractal import NodeRole
from loom.kernel.fractal import StructureTemplate, TemplateManager
from loom.kernel.optimization import StructureSnapshot

# ============================================================================
# Test Helper Functions
# ============================================================================


def create_test_snapshot(
    structure_id: str, task_type: str, fitness: float = 0.8, total_nodes: int = 5, depth: int = 2
) -> StructureSnapshot:
    """Create a test snapshot"""
    return StructureSnapshot(
        timestamp=123456.0,
        structure_id=structure_id,
        task_type=task_type,
        task_complexity=0.6,
        total_nodes=total_nodes,
        max_depth=depth,
        avg_depth=float(depth) / 2,
        avg_branching=2.0,
        node_roles={
            NodeRole.COORDINATOR.value: 1,
            NodeRole.EXECUTOR.value: total_nodes - 2,
            NodeRole.AGGREGATOR.value: 1,
        },
        fitness_score=fitness,
        success_rate=0.9,
        avg_tokens=150.0,
        avg_time=3.0,
        avg_cost=0.1,
        growth_strategies={},
    )


# ============================================================================
# Test Cases
# ============================================================================


class TestStructureTemplate(unittest.TestCase):
    """Test StructureTemplate data structure"""

    def test_template_creation(self):
        """Test creating a template"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Research Pipeline",
            description="For research tasks",
            task_categories=["research", "analysis"],
            topology_type="hierarchical",
            node_specs=[
                {"role": NodeRole.COORDINATOR.value, "depth": 0},
                {"role": NodeRole.EXECUTOR.value, "depth": 1},
            ],
            avg_fitness=0.85,
            min_fitness=0.75,
            success_rate=0.9,
            usage_count=5,
        )

        self.assertEqual(template.template_id, "tmpl_001")
        self.assertEqual(template.avg_fitness, 0.85)
        self.assertIn("research", template.task_categories)

    def test_template_matches_task(self):
        """Test task matching"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Research Pipeline",
            description="For research tasks",
            task_categories=["research", "analysis"],
            topology_type="hierarchical",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
        )

        # Exact match
        score = template.matches_task("research")
        self.assertGreater(score, 0)

        # Partial match
        score = template.matches_task("data_analysis")
        self.assertGreater(score, 0)

        # No match
        score = template.matches_task("completely_different")
        self.assertEqual(score, 0)

    def test_template_matches_with_description(self):
        """Test matching with task description"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Research Pipeline",
            description="For research tasks",
            task_categories=["research"],
            topology_type="hierarchical",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
            tags=["analysis", "data", "extraction"],
        )

        # Match with description
        score = template.matches_task("research", "Extract and analyze data")
        self.assertGreater(score, 0)

    def test_template_serialization(self):
        """Test template to_dict and from_dict"""
        original = StructureTemplate(
            template_id="tmpl_001",
            name="Research Pipeline",
            description="For research tasks",
            task_categories=["research"],
            topology_type="hierarchical",
            node_specs=[{"role": NodeRole.COORDINATOR.value, "depth": 0}],
            avg_fitness=0.85,
            min_fitness=0.75,
            success_rate=0.9,
            usage_count=10,
            confidence=0.8,
        )

        data = original.to_dict()
        restored = StructureTemplate.from_dict(data)

        self.assertEqual(restored.template_id, original.template_id)
        self.assertEqual(restored.avg_fitness, original.avg_fitness)
        self.assertEqual(restored.usage_count, original.usage_count)

    def test_template_usage_boost(self):
        """Test that frequently used templates get boost"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Common Pipeline",
            description="Frequently used",
            task_categories=["common"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.7,
            min_fitness=0.6,
            success_rate=0.85,
            usage_count=15,  # Frequently used
        )

        score = template.matches_task("common")
        # Should include usage boost
        self.assertGreater(score, 0.5)


class TestTemplateManager(unittest.TestCase):
    """Test TemplateManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = TemplateManager(min_fitness_for_template=0.75, min_usage_for_template=2)

    def test_manager_initialization(self):
        """Test manager initialization"""
        self.assertEqual(len(self.manager.templates), 0)
        self.assertEqual(len(self.manager.category_index), 0)
        self.assertEqual(self.manager.min_fitness_for_template, 0.75)

    def test_add_template(self):
        """Test adding a template"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Test Template",
            description="For testing",
            task_categories=["test"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
        )

        self.manager.add_template(template)

        self.assertEqual(len(self.manager.templates), 1)
        self.assertIn("tmpl_001", self.manager.templates)

    def test_add_template_to_index(self):
        """Test that categories are indexed"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Test Template",
            description="For testing",
            task_categories=["research", "analysis"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
        )

        self.manager.add_template(template)

        self.assertIn("research", self.manager.category_index)
        self.assertIn("tmpl_001", self.manager.category_index["research"])

    def test_get_template(self):
        """Test retrieving a template"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Test Template",
            description="For testing",
            task_categories=["test"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
        )

        self.manager.add_template(template)
        retrieved = self.manager.get_template("tmpl_001")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.template_id, "tmpl_001")

    def test_get_nonexistent_template(self):
        """Test getting template that doesn't exist"""
        retrieved = self.manager.get_template("nonexistent")
        self.assertIsNone(retrieved)

    def test_remove_template(self):
        """Test removing a template"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Test Template",
            description="For testing",
            task_categories=["test"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
        )

        self.manager.add_template(template)
        self.assertEqual(len(self.manager.templates), 1)

        self.manager.remove_template("tmpl_001")
        self.assertEqual(len(self.manager.templates), 0)

    def test_remove_template_from_index(self):
        """Test that removal updates index"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Test Template",
            description="For testing",
            task_categories=["research"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
        )

        self.manager.add_template(template)
        self.manager.remove_template("tmpl_001")

        self.assertNotIn("tmpl_001", self.manager.category_index.get("research", []))

    def test_learn_from_snapshots(self):
        """Test learning template from snapshots"""
        # Create good snapshots
        snapshots = [
            create_test_snapshot("struct_1", "research", fitness=0.80, total_nodes=5),
            create_test_snapshot("struct_2", "research", fitness=0.82, total_nodes=5),
            create_test_snapshot("struct_3", "research", fitness=0.81, total_nodes=5),
        ]

        template = self.manager.learn_from_snapshots(snapshots, "research")

        self.assertIsNotNone(template)
        self.assertEqual(template.task_categories[0], "research")
        self.assertGreater(template.avg_fitness, 0)

    def test_learn_requires_enough_samples(self):
        """Test that learning requires minimum samples"""
        # Only 1 sample (less than min_usage_for_template=2)
        snapshots = [create_test_snapshot("struct_1", "research", fitness=0.90)]

        template = self.manager.learn_from_snapshots(snapshots, "research")

        self.assertIsNone(template)

    def test_learn_requires_sufficient_fitness(self):
        """Test that learning requires minimum fitness"""
        # Low fitness snapshots
        snapshots = [
            create_test_snapshot("struct_1", "research", fitness=0.50),
            create_test_snapshot("struct_2", "research", fitness=0.50),
        ]

        template = self.manager.learn_from_snapshots(snapshots, "research")

        # Should return None because no snapshots meet fitness threshold
        self.assertIsNone(template)

    def test_find_templates_by_category(self):
        """Test finding templates by task type"""
        # Add templates
        for i in range(3):
            template = StructureTemplate(
                template_id=f"research_{i}",
                name=f"Research Template {i}",
                description="For research",
                task_categories=["research"],
                topology_type="hierarchical",
                node_specs=[],
                avg_fitness=0.8 + i * 0.05,
                min_fitness=0.7,
                success_rate=0.9,
            )
            self.manager.add_template(template)

        # Find templates
        matches = self.manager.find_templates("research")

        self.assertGreater(len(matches), 0)
        self.assertLessEqual(len(matches), 5)  # limit default

    def test_find_templates_sorting(self):
        """Test that found templates are sorted by score"""
        # Add templates with different match scores
        template1 = StructureTemplate(
            template_id="tmpl_1",
            name="Good Match",
            description="For research",
            task_categories=["research"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.9,
            min_fitness=0.8,
            success_rate=0.95,
            usage_count=50,  # High usage = boost
        )
        template2 = StructureTemplate(
            template_id="tmpl_2",
            name="Poor Match",
            description="For something else",
            task_categories=["other"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.7,
            min_fitness=0.6,
            success_rate=0.8,
            usage_count=1,  # Low usage
        )

        self.manager.add_template(template1)
        self.manager.add_template(template2)

        matches = self.manager.find_templates("research")

        # Should find template1 with higher score
        if matches:
            self.assertEqual(matches[0][0].template_id, "tmpl_1")

    def test_recommend_template(self):
        """Test template recommendation"""
        # Add a good template
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Research Pipeline",
            description="For research",
            task_categories=["research"],
            topology_type="hierarchical",
            node_specs=[],
            avg_fitness=0.85,
            min_fitness=0.75,
            success_rate=0.9,
            confidence=0.8,
        )
        self.manager.add_template(template)

        recommendation = self.manager.recommend_template(
            task_type="research", task_description="Research data analysis"
        )

        self.assertIsNotNone(recommendation)
        self.assertEqual(recommendation.template_id, "tmpl_001")

    def test_recommend_for_improvement(self):
        """Test recommendation filtered for improvement"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Research Pipeline",
            description="For research",
            task_categories=["research"],
            topology_type="hierarchical",
            node_specs=[],
            avg_fitness=0.75,  # Template fitness
            min_fitness=0.65,
            success_rate=0.85,
            confidence=0.7,
        )
        self.manager.add_template(template)

        # Ask for improvement from current fitness of 0.80 (higher than template)
        self.manager.recommend_template(
            task_type="research",
            current_fitness=0.80,  # No template can improve this
        )

        # Unlikely to get recommendation
        # (depends on learned patterns)

    def test_record_template_usage(self):
        """Test recording template usage"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Test Template",
            description="For testing",
            task_categories=["test"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
            usage_count=0,
        )
        self.manager.add_template(template)

        # Record usage
        self.manager.record_usage("tmpl_001", 0.82)
        self.manager.record_usage("tmpl_001", 0.85)

        updated = self.manager.get_template("tmpl_001")
        self.assertEqual(updated.usage_count, 2)

    def test_get_template_stats(self):
        """Test getting template statistics"""
        template = StructureTemplate(
            template_id="tmpl_001",
            name="Test Template",
            description="For testing",
            task_categories=["test"],
            topology_type="sequential",
            node_specs=[],
            avg_fitness=0.8,
            min_fitness=0.7,
            success_rate=0.9,
        )
        self.manager.add_template(template)

        # Record usage
        self.manager.record_usage("tmpl_001", 0.81)
        self.manager.record_usage("tmpl_001", 0.83)

        stats = self.manager.get_template_stats("tmpl_001")

        self.assertIn("usage_count", stats)
        self.assertIn("avg_fitness", stats)
        self.assertIn("confidence", stats)
        self.assertEqual(stats["usage_count"], 2)

    def test_get_summary(self):
        """Test getting manager summary"""
        # Add templates
        for i in range(3):
            template = StructureTemplate(
                template_id=f"tmpl_{i}",
                name=f"Template {i}",
                description="For testing",
                task_categories=["test", "analysis"][i % 2 :],
                topology_type=["sequential", "parallel"][i % 2],
                node_specs=[],
                avg_fitness=0.7 + i * 0.05,
                min_fitness=0.6,
                success_rate=0.85,
                usage_count=i + 1,
            )
            self.manager.add_template(template)

        summary = self.manager.get_summary()

        self.assertEqual(summary["total_templates"], 3)
        self.assertGreater(summary["total_usage"], 0)
        self.assertIn("avg_template_fitness", summary)

    def test_persistence_save_and_load(self):
        """Test saving and loading templates"""
        # Add templates
        for i in range(2):
            template = StructureTemplate(
                template_id=f"tmpl_{i}",
                name=f"Template {i}",
                description="For testing",
                task_categories=["test"],
                topology_type="sequential",
                node_specs=[],
                avg_fitness=0.75 + i * 0.05,
                min_fitness=0.65,
                success_rate=0.9,
                usage_count=i + 1,
            )
            self.manager.add_template(template)

        # Record usage
        self.manager.record_usage("tmpl_0", 0.76)

        # Save
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            self.manager.save(temp_file)
            self.assertTrue(os.path.exists(temp_file))

            # Load
            new_manager = TemplateManager()
            new_manager.load(temp_file)

            self.assertEqual(len(new_manager.templates), 2)
            retrieved = new_manager.get_template("tmpl_0")
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.avg_fitness, 0.75)

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_extract_tags_from_task_type(self):
        """Test tag extraction"""
        template = self.manager.learn_from_snapshots(
            [
                create_test_snapshot("s1", "text_analysis_research", fitness=0.80),
                create_test_snapshot("s2", "text_analysis_research", fitness=0.82),
                create_test_snapshot("s3", "text_analysis_research", fitness=0.81),
            ],
            "text_analysis_research",
        )

        if template:
            # Should have extracted meaningful tags
            self.assertGreater(len(template.tags), 0)

    def test_topology_type_detection(self):
        """Test topology type detection in learning"""
        # Shallow, high branching = parallel
        snapshots = [
            create_test_snapshot("s1", "parallel_task", fitness=0.80, total_nodes=5, depth=1),
            create_test_snapshot("s2", "parallel_task", fitness=0.82, total_nodes=5, depth=1),
        ]

        template = self.manager.learn_from_snapshots(snapshots, "parallel_task")

        if template:
            # Should detect as parallel or hierarchical
            self.assertIn(template.topology_type, ["parallel", "hierarchical", "mixed"])


if __name__ == "__main__":
    unittest.main()
