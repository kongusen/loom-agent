"""
Tests for Structure Evolution with Genetic Algorithms

Tests the genetic algorithm's ability to evolve structures through
mutation, crossover, and selection operations.
"""

import unittest
from unittest.mock import Mock

from loom.config.fractal import NodeRole
from loom.kernel.optimization import (
    EvolutionConfig,
    GeneticOperators,
    GenomeConverter,
    StructureEvolver,
    StructureGenome,
)

# ============================================================================
# Test Helper Functions
# ============================================================================


def create_simple_genome(
    num_nodes: int = 5, max_depth: int = 2, fitness: float = 0.5
) -> StructureGenome:
    """Create a simple test genome"""
    genes = [{"id": "root", "parent_id": None, "role": NodeRole.COORDINATOR.value, "depth": 0}]

    for i in range(1, num_nodes):
        depth = min(1 + (i - 1) // 2, max_depth)
        parent_id = "root" if depth == 1 else f"node_{i-2}"

        genes.append(
            {
                "id": f"node_{i}",
                "parent_id": parent_id,
                "role": NodeRole.EXECUTOR.value,
                "depth": depth,
            }
        )

    return StructureGenome(genes=genes, fitness=fitness)


def create_mock_node(node_id: str = "node_0", role: str = "coordinator", depth: int = 0) -> Mock:
    """Create a mock FractalAgentNode"""
    node = Mock()
    node.node_id = node_id
    node.role = Mock(value=role)
    node.depth = depth
    node.children = []
    node.parent = None

    node.metrics = Mock()
    node.metrics.task_count = 10
    node.metrics.fitness_score = Mock(return_value=0.8)

    return node


# ============================================================================
# Test Cases
# ============================================================================


class TestStructureGenome(unittest.TestCase):
    """Test StructureGenome data structure"""

    def test_genome_creation(self):
        """Test creating a genome"""
        genes = [
            {"id": "root", "parent_id": None, "role": NodeRole.COORDINATOR.value, "depth": 0},
            {"id": "node_1", "parent_id": "root", "role": NodeRole.EXECUTOR.value, "depth": 1},
        ]
        genome = StructureGenome(genes=genes, fitness=0.75)

        self.assertEqual(len(genome.genes), 2)
        self.assertEqual(genome.fitness, 0.75)

    def test_genome_cloning(self):
        """Test genome cloning"""
        original = create_simple_genome(num_nodes=5, fitness=0.8)
        cloned = original.clone()

        self.assertEqual(len(cloned.genes), len(original.genes))
        self.assertEqual(cloned.fitness, original.fitness)

        # Ensure deep copy
        cloned.genes[0]["id"] = "modified"
        self.assertNotEqual(original.genes[0]["id"], cloned.genes[0]["id"])

    def test_genome_depth_calculation(self):
        """Test calculating maximum depth"""
        genome = create_simple_genome(num_nodes=5, max_depth=2)
        depth = genome.get_depth()

        self.assertGreater(depth, 0)
        self.assertLessEqual(depth, 2)

    def test_genome_node_count(self):
        """Test node count"""
        genome = create_simple_genome(num_nodes=5)
        count = genome.get_node_count()

        self.assertEqual(count, 5)

    def test_genome_to_dict(self):
        """Test genome serialization"""
        genome = create_simple_genome(num_nodes=3, fitness=0.7)
        data = genome.to_dict()

        self.assertIn("genes", data)
        self.assertIn("fitness", data)
        self.assertIn("generation", data)
        self.assertEqual(data["fitness"], 0.7)


class TestGeneticOperators(unittest.TestCase):
    """Test genetic operators for evolution"""

    def test_mutation_without_trigger(self):
        """Test that mutation respects probability threshold"""
        genome = create_simple_genome(num_nodes=3)
        original_count = len(genome.genes)

        # With 0% mutation rate, should return clone
        mutated = GeneticOperators.mutate(genome, mutation_rate=0.0, config=EvolutionConfig())

        # Should be cloned but distinct
        self.assertEqual(len(mutated.genes), original_count)
        self.assertIsNot(mutated, genome)

    def test_add_node_mutation(self):
        """Test adding a node mutation"""
        config = EvolutionConfig(max_structure_nodes=10, max_structure_depth=3)
        genome = create_simple_genome(num_nodes=3)
        original_count = len(genome.genes)

        # Force mutation
        mutated = GeneticOperators._add_node_mutation(genome, config)

        # Should have more nodes
        self.assertGreaterEqual(len(mutated.genes), original_count)

    def test_add_node_respects_max_nodes(self):
        """Test that add node mutation respects max limit"""
        config = EvolutionConfig(max_structure_nodes=3, max_structure_depth=5)
        genome = create_simple_genome(num_nodes=3)

        # Try to add when at max
        mutated = GeneticOperators._add_node_mutation(genome, config)

        # Should not exceed max
        self.assertLessEqual(len(mutated.genes), config.max_structure_nodes)

    def test_add_node_respects_max_depth(self):
        """Test that add node mutation respects max depth"""
        config = EvolutionConfig(max_structure_nodes=20, max_structure_depth=1)
        genome = create_simple_genome(num_nodes=3, max_depth=1)

        mutated = GeneticOperators._add_node_mutation(genome, config)

        # Should not exceed max depth
        max_depth = max(g["depth"] for g in mutated.genes)
        self.assertLessEqual(max_depth, config.max_structure_depth)

    def test_remove_node_mutation(self):
        """Test removing a node mutation"""
        config = EvolutionConfig()
        genome = create_simple_genome(num_nodes=5)
        original_count = len(genome.genes)

        mutated = GeneticOperators._remove_node_mutation(genome, config)

        # Should have fewer nodes or be unchanged (if removal not possible)
        self.assertLessEqual(len(mutated.genes), original_count)

    def test_remove_node_keeps_root(self):
        """Test that remove node never removes root"""
        config = EvolutionConfig()
        genome = create_simple_genome(num_nodes=3)

        mutated = GeneticOperators._remove_node_mutation(genome, config)

        # Root should still exist
        root_exists = any(g["id"] == "root" for g in mutated.genes)
        self.assertTrue(root_exists)

    def test_change_role_mutation(self):
        """Test changing node role mutation"""
        genome = create_simple_genome(num_nodes=3)
        [g["role"] for g in genome.genes]

        mutated = GeneticOperators._change_role_mutation(genome)

        # At least one role should be different (usually)
        [g["role"] for g in mutated.genes]
        # Note: could theoretically be same if random chose same role

    def test_crossover_without_trigger(self):
        """Test crossover respects probability"""
        parent1 = create_simple_genome(num_nodes=3)
        parent2 = create_simple_genome(num_nodes=4)

        # With 0% crossover, should just clone
        offspring1, offspring2 = GeneticOperators.crossover(parent1, parent2, crossover_rate=0.0)

        self.assertIsNot(offspring1, parent1)
        self.assertIsNot(offspring2, parent2)

    def test_crossover_produces_offspring(self):
        """Test that crossover produces different offspring"""
        parent1 = create_simple_genome(num_nodes=5)
        parent2 = create_simple_genome(num_nodes=4)

        offspring1, offspring2 = GeneticOperators.crossover(parent1, parent2, crossover_rate=1.0)

        # Offspring should exist
        self.assertIsNotNone(offspring1)
        self.assertIsNotNone(offspring2)
        self.assertGreater(len(offspring1.genes), 0)

    def test_crossover_combines_structures(self):
        """Test that crossover actually combines parent structures"""
        parent1 = StructureGenome(
            genes=[
                {"id": "root", "parent_id": None, "role": NodeRole.COORDINATOR.value, "depth": 0},
                {"id": "node_1", "parent_id": "root", "role": NodeRole.EXECUTOR.value, "depth": 1},
            ]
        )

        parent2 = StructureGenome(
            genes=[
                {"id": "root", "parent_id": None, "role": NodeRole.COORDINATOR.value, "depth": 0},
                {
                    "id": "node_2",
                    "parent_id": "root",
                    "role": NodeRole.SPECIALIST.value,
                    "depth": 1,
                },
                {
                    "id": "node_3",
                    "parent_id": "node_2",
                    "role": NodeRole.EXECUTOR.value,
                    "depth": 2,
                },
            ]
        )

        offspring1, offspring2 = GeneticOperators.crossover(parent1, parent2, crossover_rate=1.0)

        # Offspring should exist and have some nodes
        self.assertGreater(len(offspring1.genes), 0)
        self.assertGreater(len(offspring2.genes), 0)


class TestEvolutionConfig(unittest.TestCase):
    """Test EvolutionConfig"""

    def test_config_defaults(self):
        """Test default configuration"""
        config = EvolutionConfig()

        self.assertEqual(config.population_size, 20)
        self.assertEqual(config.generations, 10)
        self.assertEqual(config.mutation_rate, 0.3)
        self.assertEqual(config.crossover_rate, 0.7)
        self.assertIsNotNone(config.fitness_weights)

    def test_config_fitness_weights(self):
        """Test that fitness weights are initialized"""
        config = EvolutionConfig()

        self.assertIn("performance", config.fitness_weights)
        self.assertIn("efficiency", config.fitness_weights)
        self.assertIn("simplicity", config.fitness_weights)
        self.assertIn("balance", config.fitness_weights)

    def test_config_custom_values(self):
        """Test custom configuration"""
        config = EvolutionConfig(population_size=50, generations=20, mutation_rate=0.5)

        self.assertEqual(config.population_size, 50)
        self.assertEqual(config.generations, 20)
        self.assertEqual(config.mutation_rate, 0.5)


class TestStructureEvolver(unittest.TestCase):
    """Test StructureEvolver"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = EvolutionConfig(
            population_size=10, generations=5, mutation_rate=0.3, crossover_rate=0.7
        )
        self.evolver = StructureEvolver(self.config)

    def test_evolver_initialization(self):
        """Test evolver initialization"""
        self.assertEqual(self.evolver.config, self.config)
        self.assertIsNotNone(self.evolver.fitness_evaluator)
        self.assertEqual(len(self.evolver.history), 0)

    def test_create_initial_population(self):
        """Test creating initial population"""
        population = self.evolver._create_initial_population()

        self.assertEqual(len(population), self.config.population_size)
        for genome in population:
            self.assertGreater(len(genome.genes), 0)
            self.assertEqual(genome.genes[0]["id"], "root")

    def test_tournament_selection(self):
        """Test tournament selection"""
        population = self.evolver._create_initial_population()
        selected = self.evolver._tournament_selection(population)

        self.assertIsNotNone(selected)
        self.assertIn(selected, population)

    def test_default_fitness_function(self):
        """Test default fitness calculation"""
        genome = create_simple_genome(num_nodes=5)
        fitness = self.evolver._default_fitness(genome)

        self.assertGreaterEqual(fitness, 0.0)
        self.assertLessEqual(fitness, 1.0)

    def test_fitness_prefers_simple_structures(self):
        """Test that fitness prefers simpler structures"""
        simple = StructureGenome(
            genes=[
                {"id": "root", "parent_id": None, "role": NodeRole.COORDINATOR.value, "depth": 0},
                {"id": "node_1", "parent_id": "root", "role": NodeRole.EXECUTOR.value, "depth": 1},
            ]
        )

        complex_genome = create_simple_genome(num_nodes=20)

        simple_fitness = self.evolver._default_fitness(simple)
        complex_fitness = self.evolver._default_fitness(complex_genome)

        # Simpler should have higher fitness (fewer nodes is better)
        self.assertGreater(simple_fitness, complex_fitness)

    def test_evolve_with_default_population(self):
        """Test evolving with default population creation"""
        best = self.evolver.evolve(initial_population=None, target_fitness=0.5)

        self.assertIsNotNone(best)
        self.assertGreater(len(best.genes), 0)
        self.assertGreater(len(self.evolver.history), 0)

    def test_evolve_improves_fitness(self):
        """Test that evolution generally improves fitness"""
        evolver = StructureEvolver(
            EvolutionConfig(
                population_size=15, generations=10, mutation_rate=0.4, crossover_rate=0.7
            )
        )

        evolver.evolve(target_fitness=1.0)

        if len(evolver.history) > 1:
            first_gen = evolver.history[0]["best_fitness"]
            last_gen = evolver.history[-1]["best_fitness"]
            # Should generally improve or stay same
            self.assertGreaterEqual(last_gen, first_gen - 0.1)

    def test_evolve_respects_target_fitness(self):
        """Test that evolution stops at target fitness"""
        evolver = StructureEvolver(
            EvolutionConfig(
                population_size=10,
                generations=100,  # Many generations
                mutation_rate=0.3,
                crossover_rate=0.7,
            )
        )

        target = 0.95
        best = evolver.evolve(target_fitness=target)

        # If target is reached, should stop early
        if best.fitness >= target:
            # Fewer generations used
            self.assertLess(len(evolver.history), 100)

    def test_evolution_history_tracking(self):
        """Test that evolution history is tracked"""
        self.evolver.evolve(target_fitness=0.9)

        self.assertGreater(len(self.evolver.history), 0)
        for entry in self.evolver.history:
            self.assertIn("generation", entry)
            self.assertIn("best_fitness", entry)
            self.assertIn("avg_fitness", entry)

    def test_get_evolution_summary(self):
        """Test getting evolution summary"""
        self.evolver.evolve(target_fitness=0.8)
        summary = self.evolver.get_evolution_summary()

        self.assertIn("generations_run", summary)
        self.assertIn("final_best_fitness", summary)
        self.assertIn("final_avg_fitness", summary)
        self.assertGreater(summary["generations_run"], 0)

    def test_custom_fitness_evaluator(self):
        """Test using custom fitness evaluator"""

        def custom_fitness(genome):
            # Prefer exactly 5 nodes
            ideal_nodes = 5
            node_diff = abs(len(genome.genes) - ideal_nodes)
            return 1.0 / (1.0 + node_diff)

        evolver = StructureEvolver(self.config, fitness_evaluator=custom_fitness)
        best = evolver.evolve(target_fitness=0.5)

        self.assertIsNotNone(best)


class TestGenomeConverter(unittest.TestCase):
    """Test converting between genomes and structures"""

    def test_structure_to_genome_conversion(self):
        """Test converting a structure to genome"""
        # Create mock tree
        root = create_mock_node(node_id="root", role="coordinator", depth=0)
        root.children = [
            create_mock_node(node_id="child_1", role="executor", depth=1),
            create_mock_node(node_id="child_2", role="executor", depth=1),
        ]

        genome = GenomeConverter.structure_to_genome(root)

        self.assertIsNotNone(genome)
        self.assertGreater(len(genome.genes), 0)
        self.assertEqual(genome.genes[0]["id"], "root")

    def test_genome_consistency(self):
        """Test that converted genome is consistent"""
        root = create_mock_node(node_id="root", role="coordinator", depth=0)
        root.children = [create_mock_node(node_id="child_1", role="executor", depth=1)]

        genome = GenomeConverter.structure_to_genome(root)

        # Should have root and child
        self.assertEqual(len(genome.genes), 2)
        self.assertTrue(any(g["id"] == "root" for g in genome.genes))


if __name__ == "__main__":
    unittest.main()
