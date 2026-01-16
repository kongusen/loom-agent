"""
Structure Evolution - Genetic Algorithm for Structure Optimization

Evolves fractal node structures using genetic algorithms to discover
optimal configurations for different task types.
"""

import copy
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from loom.config.fractal import FractalConfig, NodeRole

logger = logging.getLogger(__name__)


# ============================================================================
# Evolution Configuration
# ============================================================================


class MutationType(Enum):
    """Types of mutations"""

    ADD_NODE = "add_node"
    REMOVE_NODE = "remove_node"
    CHANGE_ROLE = "change_role"
    CHANGE_DEPTH = "change_depth"


@dataclass
class EvolutionConfig:
    """Configuration for genetic algorithm"""

    population_size: int = 20
    """Size of population"""

    generations: int = 10
    """Number of generations"""

    mutation_rate: float = 0.3
    """Probability of mutation"""

    crossover_rate: float = 0.7
    """Probability of crossover"""

    elitism_count: int = 2
    """Number of elite individuals to preserve"""

    tournament_size: int = 3
    """Size of tournament for selection"""

    max_structure_depth: int = 4
    """Maximum allowed structure depth"""

    max_structure_nodes: int = 20
    """Maximum nodes in structure"""

    fitness_weights: dict[str, float] | None = None
    """Weights for fitness calculation"""

    def __post_init__(self):
        if self.fitness_weights is None:
            self.fitness_weights = {
                "performance": 0.4,
                "efficiency": 0.3,
                "simplicity": 0.2,
                "balance": 0.1,
            }


# ============================================================================
# Structure Genome
# ============================================================================


@dataclass
class StructureGenome:
    """
    Genetic representation of a structure

    Simplified representation that can be evolved and converted to/from
    actual FractalAgentNode structures.
    """

    genes: list[dict[str, Any]]  # Each gene represents a node
    fitness: float = 0.0
    generation: int = 0

    def clone(self) -> "StructureGenome":
        """Create a deep copy"""
        return StructureGenome(
            genes=copy.deepcopy(self.genes), fitness=self.fitness, generation=self.generation
        )

    def get_depth(self) -> int:
        """Get maximum depth"""
        if not self.genes:
            return 0
        return int(max(gene["depth"] for gene in self.genes))

    def get_node_count(self) -> int:
        """Get total node count"""
        return len(self.genes)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {"genes": self.genes, "fitness": self.fitness, "generation": self.generation}


# ============================================================================
# Genetic Operators
# ============================================================================


class GeneticOperators:
    """Genetic operators for structure evolution"""

    @staticmethod
    def mutate(
        genome: StructureGenome, mutation_rate: float, config: EvolutionConfig
    ) -> StructureGenome:
        """
        Mutate a genome

        Args:
            genome: Genome to mutate
            mutation_rate: Probability of mutation
            config: Evolution configuration

        Returns:
            Mutated genome
        """
        if random.random() > mutation_rate:
            return genome.clone()

        mutated = genome.clone()

        # Choose mutation type
        mutation_types = list(MutationType)
        mutation = random.choice(mutation_types)

        if mutation == MutationType.ADD_NODE:
            mutated = GeneticOperators._add_node_mutation(mutated, config)

        elif mutation == MutationType.REMOVE_NODE:
            mutated = GeneticOperators._remove_node_mutation(mutated, config)

        elif mutation == MutationType.CHANGE_ROLE:
            mutated = GeneticOperators._change_role_mutation(mutated)

        elif mutation == MutationType.CHANGE_DEPTH:
            mutated = GeneticOperators._change_depth_mutation(mutated, config)

        logger.debug(
            f"Mutation: {mutation.value}, nodes: {len(genome.genes)} -> {len(mutated.genes)}"
        )

        return mutated

    @staticmethod
    def _add_node_mutation(genome: StructureGenome, config: EvolutionConfig) -> StructureGenome:
        """Add a random node"""
        if len(genome.genes) >= config.max_structure_nodes:
            return genome  # Can't add more

        mutated = genome.clone()

        # Choose parent node (any existing node)
        if mutated.genes:
            parent = random.choice(mutated.genes)
            parent_depth = parent["depth"]

            # Check depth limit
            if parent_depth + 1 >= config.max_structure_depth:
                return genome  # Can't go deeper

            # Create new node
            new_node = {
                "id": f"node_{len(mutated.genes)}",
                "parent_id": parent["id"],
                "role": random.choice(list(NodeRole)).value,
                "depth": parent_depth + 1,
            }

            mutated.genes.append(new_node)

        return mutated

    @staticmethod
    def _remove_node_mutation(genome: StructureGenome, _config: EvolutionConfig) -> StructureGenome:
        """Remove a random node"""
        if len(genome.genes) <= 1:
            return genome  # Must keep at least one node

        mutated = genome.clone()

        # Don't remove root
        non_root_genes = [g for g in mutated.genes if g.get("parent_id") is not None]

        if non_root_genes:
            to_remove = random.choice(non_root_genes)

            # Remove this node and all its descendants
            def is_descendant(node: dict, ancestor_id: str) -> bool:
                if node["id"] == ancestor_id:
                    return True
                parent_id = node.get("parent_id")
                if parent_id:
                    parent = next((g for g in mutated.genes if g["id"] == parent_id), None)
                    if parent:
                        return is_descendant(parent, ancestor_id)
                return False

            mutated.genes = [
                g
                for g in mutated.genes
                if g["id"] != to_remove["id"] and not is_descendant(g, to_remove["id"])
            ]

        return mutated

    @staticmethod
    def _change_role_mutation(genome: StructureGenome) -> StructureGenome:
        """Change role of a random node"""
        if not genome.genes:
            return genome

        mutated = genome.clone()

        # Choose random node
        node = random.choice(mutated.genes)

        # Change to different role
        current_role = node["role"]
        other_roles = [r.value for r in NodeRole if r.value != current_role]

        if other_roles:
            node["role"] = random.choice(other_roles)

        return mutated

    @staticmethod
    def _change_depth_mutation(
        genome: StructureGenome, _config: EvolutionConfig
    ) -> StructureGenome:
        """Move a subtree to a different depth"""
        # This is complex - skip for now
        return genome

    @staticmethod
    def crossover(
        parent1: StructureGenome, parent2: StructureGenome, crossover_rate: float
    ) -> tuple[StructureGenome, StructureGenome]:
        """
        Perform crossover between two genomes

        Args:
            parent1: First parent
            parent2: Second parent
            crossover_rate: Probability of crossover

        Returns:
            Two offspring
        """
        if random.random() > crossover_rate:
            return parent1.clone(), parent2.clone()

        # Single-point crossover at depth level
        offspring1 = parent1.clone()
        offspring2 = parent2.clone()

        # Find common depths
        depths1 = {g["depth"] for g in parent1.genes}
        depths2 = {g["depth"] for g in parent2.genes}
        common_depths = list(depths1 & depths2)

        if len(common_depths) > 1:
            # Choose crossover depth
            crossover_depth = random.choice(common_depths[1:])  # Skip root

            # Swap subtrees at this depth
            subtree1 = [g for g in parent1.genes if g["depth"] >= crossover_depth]
            subtree2 = [g for g in parent2.genes if g["depth"] >= crossover_depth]

            # Create offspring
            offspring1.genes = [g for g in parent1.genes if g["depth"] < crossover_depth] + subtree2
            offspring2.genes = [g for g in parent2.genes if g["depth"] < crossover_depth] + subtree1

            logger.debug(f"Crossover at depth {crossover_depth}")

        return offspring1, offspring2


# ============================================================================
# Structure Evolver
# ============================================================================


class StructureEvolver:
    """
    Evolves fractal structures using genetic algorithms
    """

    def __init__(
        self,
        config: EvolutionConfig,
        fitness_evaluator: Callable[[StructureGenome], float] | None = None,
    ):
        """
        Initialize evolver

        Args:
            config: Evolution configuration
            fitness_evaluator: Function to evaluate fitness (optional)
        """
        self.config = config
        self.fitness_evaluator = fitness_evaluator or self._default_fitness

        # Evolution history
        self.history: list[dict[str, Any]] = []

    def evolve(
        self, initial_population: list[StructureGenome] | None = None, target_fitness: float = 0.9
    ) -> StructureGenome:
        """
        Evolve structures using genetic algorithm

        Args:
            initial_population: Starting population (random if None)
            target_fitness: Target fitness to reach

        Returns:
            Best genome found
        """
        # Initialize population
        if initial_population is None:
            population = self._create_initial_population()
        else:
            population = [g.clone() for g in initial_population]

        logger.info(
            f"Starting evolution: population={len(population)}, generations={self.config.generations}"
        )

        best_genome = None
        best_fitness = 0.0

        for generation in range(self.config.generations):
            # Evaluate fitness
            for genome in population:
                genome.fitness = self.fitness_evaluator(genome)
                genome.generation = generation

            # Track best
            generation_best = max(population, key=lambda g: g.fitness)
            if generation_best.fitness > best_fitness:
                best_genome = generation_best.clone()
                best_fitness = generation_best.fitness

            # Record history
            avg_fitness = np.mean([g.fitness for g in population])
            self.history.append(
                {
                    "generation": generation,
                    "best_fitness": generation_best.fitness,
                    "avg_fitness": avg_fitness,
                    "population_size": len(population),
                }
            )

            logger.info(
                f"Generation {generation}: best={generation_best.fitness:.3f}, "
                f"avg={avg_fitness:.3f}"
            )

            # Check if target reached
            if best_fitness >= target_fitness:
                logger.info(f"Target fitness {target_fitness} reached!")
                break

            # Create next generation
            population = self._create_next_generation(population)

        logger.info(f"Evolution complete: best fitness={best_fitness:.3f}")

        # Ensure we always return a genome (fallback to best from final population)
        if best_genome is None and population:
            best_genome = max(population, key=lambda g: g.fitness)

        if best_genome is None:
            raise RuntimeError("Evolution failed: no valid genome found")

        return best_genome

    def _create_initial_population(self) -> list[StructureGenome]:
        """Create random initial population"""
        population = []

        for _i in range(self.config.population_size):
            # Create random structure
            genes = []

            # Root node
            genes.append(
                {"id": "root", "parent_id": None, "role": NodeRole.COORDINATOR.value, "depth": 0}
            )

            # Add random children
            num_children = random.randint(1, 4)
            for j in range(num_children):
                genes.append(
                    {
                        "id": f"node_{j}",
                        "parent_id": "root",
                        "role": random.choice(list(NodeRole)).value,
                        "depth": 1,
                    }
                )

            genome = StructureGenome(genes=genes)
            population.append(genome)

        return population

    def _create_next_generation(self, population: list[StructureGenome]) -> list[StructureGenome]:
        """Create next generation using selection, crossover, and mutation"""
        next_gen = []

        # Elitism: keep best individuals
        sorted_pop = sorted(population, key=lambda g: g.fitness, reverse=True)
        next_gen.extend([g.clone() for g in sorted_pop[: self.config.elitism_count]])

        # Fill rest with offspring
        while len(next_gen) < self.config.population_size:
            # Selection
            parent1 = self._tournament_selection(population)
            parent2 = self._tournament_selection(population)

            # Crossover
            offspring1, offspring2 = GeneticOperators.crossover(
                parent1, parent2, self.config.crossover_rate
            )

            # Mutation
            offspring1 = GeneticOperators.mutate(offspring1, self.config.mutation_rate, self.config)
            offspring2 = GeneticOperators.mutate(offspring2, self.config.mutation_rate, self.config)

            next_gen.append(offspring1)
            if len(next_gen) < self.config.population_size:
                next_gen.append(offspring2)

        return next_gen[: self.config.population_size]

    def _tournament_selection(self, population: list[StructureGenome]) -> StructureGenome:
        """Select individual using tournament selection"""
        tournament = random.sample(population, self.config.tournament_size)
        winner = max(tournament, key=lambda g: g.fitness)
        return winner

    def _default_fitness(self, genome: StructureGenome) -> float:
        """
        Default fitness function

        Evaluates based on:
        - Simplicity (fewer nodes is better)
        - Balance (consistent branching is better)
        - Depth (moderate depth is better)
        """
        weights = self.config.fitness_weights
        if weights is None:
            # Should not happen due to post_init, but for mypy:
            weights = {"performance": 0.4, "efficiency": 0.3, "simplicity": 0.2, "balance": 0.1}

        # Simplicity score
        max_nodes = self.config.max_structure_nodes
        simplicity = 1.0 - (len(genome.genes) / max_nodes)

        # Depth score (prefer depth 2-3)
        depth = genome.get_depth()
        if depth == 2 or depth == 3:
            depth_score = 1.0
        elif depth == 1:
            depth_score = 0.7
        elif depth >= 4:
            depth_score = 0.5
        else:
            depth_score = 0.3

        # Balance score (check if branching is consistent)
        # Count children per parent
        children_counts: dict[Any, int] = {}
        for gene in genome.genes:
            parent_id = gene.get("parent_id")
            if parent_id:
                children_counts[parent_id] = children_counts.get(parent_id, 0) + 1

        if children_counts:
            np.mean(list(children_counts.values()))
            std_children = float(np.std(list(children_counts.values())))
            balance = 1.0 / (1.0 + std_children)  # Lower std = better balance
        else:
            balance = 1.0

        # Combine
        fitness = (
            simplicity * weights["simplicity"]
            + depth_score * weights["balance"]
            + balance * weights["efficiency"]
        )

        return float(min(1.0, max(0.0, fitness)))

    def get_evolution_summary(self) -> dict[str, Any]:
        """Get summary of evolution process"""
        if not self.history:
            return {}

        best_fitnesses = [h["best_fitness"] for h in self.history]
        avg_fitnesses = [h["avg_fitness"] for h in self.history]

        return {
            "generations_run": len(self.history),
            "final_best_fitness": best_fitnesses[-1],
            "final_avg_fitness": avg_fitnesses[-1],
            "fitness_improvement": best_fitnesses[-1] - best_fitnesses[0],
            "convergence_speed": self._calculate_convergence_speed(best_fitnesses),
        }

    def _calculate_convergence_speed(self, fitnesses: list[float]) -> float:
        """Calculate how quickly the algorithm converged"""
        if len(fitnesses) < 2:
            return 0.0

        # Measure improvement in first half vs second half
        mid = len(fitnesses) // 2
        first_half_improvement = fitnesses[mid] - fitnesses[0]
        second_half_improvement = fitnesses[-1] - fitnesses[mid]

        if first_half_improvement == 0:
            return 0.0

        return second_half_improvement / first_half_improvement


# ============================================================================
# Genome Converter
# ============================================================================


class GenomeConverter:
    """Convert between StructureGenome and FractalAgentNode"""

    @staticmethod
    def genome_to_structure(
        genome: StructureGenome, provider: Any, config: FractalConfig
    ) -> Any:  # FractalAgentNode
        """
        Convert genome to actual structure

        Args:
            genome: Structure genome
            provider: LLM provider
            config: Fractal configuration

        Returns:
            Root FractalAgentNode
        """
        from loom.node.fractal import FractalAgentNode

        # Create nodes map
        nodes_map: dict[str, FractalAgentNode] = {}

        # Sort by depth to create parents first
        sorted_genes = sorted(genome.genes, key=lambda g: g["depth"])

        for gene in sorted_genes:
            parent_id = gene.get("parent_id")
            parent = nodes_map.get(str(parent_id)) if parent_id else None

            node = FractalAgentNode(
                node_id=gene["id"],
                provider=provider,
                role=NodeRole[gene["role"].upper()],
                parent=parent,
                depth=gene["depth"],
                fractal_config=config,
                standalone=True,
            )

            if parent:
                parent.children.append(node)

            nodes_map[gene["id"]] = node

        # Return root
        return nodes_map.get("root")

    @staticmethod
    def structure_to_genome(root: Any) -> StructureGenome:
        """
        Convert structure to genome

        Args:
            root: Root FractalAgentNode

        Returns:
            StructureGenome
        """
        genes = []

        def _collect(node: Any, parent_id: str | None = None):
            gene = {
                "id": node.node_id,
                "parent_id": parent_id,
                "role": node.role.value,
                "depth": node.depth,
            }
            genes.append(gene)

            for child in node.children:
                _collect(child, node.node_id)

        _collect(root)

        genome = StructureGenome(genes=genes)

        # Set fitness from node metrics
        if root.metrics.task_count > 0:
            genome.fitness = root.metrics.fitness_score()

        return genome
