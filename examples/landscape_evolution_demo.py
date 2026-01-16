"""
Landscape Evolution Demo - Phase 3 Examples

Comprehensive examples demonstrating:
1. Recording structure performance and learning patterns
2. Using genetic algorithm to evolve structures
3. Managing and recommending templates
4. Complete integration workflow
"""

import random
from unittest.mock import Mock

import numpy as np

from loom.config.fractal import NodeRole
from loom.kernel.fractal import TemplateManager
from loom.kernel.optimization import (
    EvolutionConfig,
    FitnessLandscapeOptimizer,
    StructureEvolver,
    StructureGenome,
)

# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_structure(
    structure_id: str,
    task_type: str,
    total_nodes: int = 5,
    max_depth: int = 2,
    fitness: float = 0.7
) -> Mock:
    """Create a mock structure for demo purposes"""
    root = Mock()
    root.node_id = "root"
    root.role = Mock(value=NodeRole.COORDINATOR.value)
    root.depth = 0
    root.children = []

    # Mock metrics
    root.metrics = Mock()
    root.metrics.task_count = 20
    root.metrics.success_rate = 0.85 + random.random() * 0.1
    root.metrics.avg_tokens = 150 + random.randint(-20, 20)
    root.metrics.avg_time = 3.0 + random.random()
    root.metrics.avg_cost = 0.1

    def mock_fitness():
        return fitness

    root.metrics.fitness_score = mock_fitness

    # Create children recursively
    def _create_children(parent, current_depth):
        if current_depth >= max_depth:
            return

        num_children = random.randint(1, 3)
        for i in range(num_children):
            child = Mock()
            child.node_id = f"node_{current_depth}_{i}"
            child.role = Mock(value=NodeRole.EXECUTOR.value)
            child.depth = current_depth + 1
            child.children = []

            child.metrics = Mock()
            child.metrics.task_count = 10
            child.metrics.success_rate = 0.85
            child.metrics.avg_tokens = 100
            child.metrics.avg_time = 2.0
            child.metrics.avg_cost = 0.05

            child.metrics.fitness_score = mock_fitness

            parent.children.append(child)
            _create_children(child, current_depth + 1)

    _create_children(root, 1)

    return root


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n{'-' * 70}")
    print(f"  {title}")
    print(f"{'-' * 70}\n")


# ============================================================================
# Example 1: Recording and Analyzing Fitness Landscape
# ============================================================================

def example_1_fitness_landscape():
    """
    Demonstrates how to record structure performance and analyze the
    fitness landscape to understand what configurations work best.
    """
    print_section("Example 1: Recording and Analyzing Fitness Landscape")

    optimizer = FitnessLandscapeOptimizer(memory_size=100)

    # Simulate recording different structures for different tasks
    task_types = ["research", "analysis", "data_extraction"]
    complexities = [0.3, 0.5, 0.7, 0.9]

    print("Recording structure performance...")
    for task_type in task_types:
        for complexity in complexities:
            # Create structures with varying fitness based on complexity match
            num_structures = 3

            for i in range(num_structures):
                # Fitness is better when structure depth matches complexity
                ideal_depth = int(2 + complexity * 3)  # 2-5 depth range
                actual_depth = random.randint(1, 4)

                # Fitness decreases if depth doesn't match complexity
                base_fitness = 0.8
                depth_penalty = abs(actual_depth - ideal_depth) * 0.1
                fitness = base_fitness - depth_penalty + random.random() * 0.1
                fitness = max(0.3, min(1.0, fitness))

                structure = create_mock_structure(
                    structure_id=f"{task_type}_{complexity}_{i}",
                    task_type=task_type,
                    total_nodes=3 + int(complexity * 5),
                    max_depth=actual_depth,
                    fitness=fitness
                )

                snapshot = optimizer.record_structure_performance(
                    root=structure,
                    task_type=task_type,
                    task_complexity=complexity,
                    structure_id=f"{task_type}_{complexity}_{i}"
                )

                print(f"  ✓ {task_type:15} | complexity={complexity:.1f} | "
                      f"depth={actual_depth} | fitness={fitness:.2f}")

    print(f"\nTotal snapshots recorded: {len(optimizer.snapshots)}")

    # Analyze and visualize landscape
    print_subsection("Fitness Landscape Visualization")
    print(optimizer.visualize_landscape())

    # Get statistics
    print_subsection("Landscape Statistics")
    stats = optimizer.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key:20}: {value:.2f}")
        else:
            print(f"  {key:20}: {value}")

    # Get best structures by task type
    print_subsection("Best Structures by Task Type")
    for task_type in task_types:
        best = optimizer.get_best_structures(task_type=task_type, limit=1)
        if best:
            snapshot = best[0]
            print(f"  {task_type:15}: nodes={snapshot.total_nodes}, "
                  f"depth={snapshot.max_depth}, fitness={snapshot.fitness_score:.2f}")

    return optimizer


# ============================================================================
# Example 2: Learning and Recommending Templates
# ============================================================================

def example_2_template_learning_and_recommendation(optimizer: FitnessLandscapeOptimizer):
    """
    Demonstrates learning templates from high-performing structures
    and using those templates to recommend configurations for new tasks.
    """
    print_section("Example 2: Learning and Recommending Templates")

    manager = TemplateManager(
        min_fitness_for_template=0.75,
        min_usage_for_template=2
    )

    # Learn templates for each task type
    print("Learning templates from high-performing structures...")

    task_types = ["research", "analysis", "data_extraction"]

    for task_type in task_types:
        # Get snapshots for this task type
        snapshots = [s for s in optimizer.snapshots if s.task_type == task_type]

        if snapshots:
            template = manager.learn_from_snapshots(snapshots, task_type)

            if template:
                print(f"  ✓ Learned template for '{task_type}'")
                print(f"    - Topology:        {template.topology_type}")
                print(f"    - Avg Fitness:     {template.avg_fitness:.2f}")
                print(f"    - Success Rate:    {template.success_rate:.2f}")
                print(f"    - Sample Count:    {template.usage_count}")
                print(f"    - Confidence:      {template.confidence:.2f}")

    # Show template library
    print_subsection("Template Library Summary")
    summary = manager.get_summary()
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"  {key:20}: {value:.2f}")
        else:
            print(f"  {key:20}: {value}")

    # Demonstrate recommendations
    print_subsection("Template Recommendations for New Tasks")

    new_tasks = [
        ("research_new", "Research data sources and compile information", 0.65),
        ("analysis_new", "Analyze market trends and patterns", 0.7),
        ("extract_new", "Extract structured data from documents", 0.6)
    ]

    for task_id, task_desc, _task_complexity in new_tasks:
        # Extract base task type
        base_task = task_id.replace("_new", "")

        recommendation = manager.recommend_template(
            task_type=base_task,
            task_description=task_desc
        )

        if recommendation:
            print(f"  Task: {task_id}")
            print(f"    Recommended: {recommendation.name}")
            print(f"    Expected Fitness: {recommendation.avg_fitness:.2f}")
            print(f"    Topology: {recommendation.topology_type}")
        else:
            print(f"  Task: {task_id} - No recommendation available")

    return manager


# ============================================================================
# Example 3: Genetic Algorithm for Structure Evolution
# ============================================================================

def example_3_structure_evolution():
    """
    Demonstrates using genetic algorithms to evolve structures
    for optimal performance.
    """
    print_section("Example 3: Structure Evolution with Genetic Algorithm")

    # Configure evolution
    config = EvolutionConfig(
        population_size=20,
        generations=15,
        mutation_rate=0.3,
        crossover_rate=0.7,
        max_structure_depth=4,
        max_structure_nodes=15
    )

    print("Evolution Configuration:")
    print(f"  Population Size:   {config.population_size}")
    print(f"  Generations:       {config.generations}")
    print(f"  Mutation Rate:     {config.mutation_rate:.2f}")
    print(f"  Crossover Rate:    {config.crossover_rate:.2f}")
    print(f"  Max Depth:         {config.max_structure_depth}")
    print(f"  Max Nodes:         {config.max_structure_nodes}")

    # Custom fitness evaluator: prefer structures with good balance
    def fitness_evaluator(genome: StructureGenome) -> float:
        """
        Evaluate fitness based on:
        - Simplicity (fewer nodes is better)
        - Depth (prefer moderate depth)
        - Balance (consistent structure)
        """
        weights = {
            'simplicity': 0.4,
            'depth': 0.3,
            'balance': 0.3
        }

        # Simplicity
        max_nodes = config.max_structure_nodes
        simplicity = 1.0 - (len(genome.genes) / max_nodes)

        # Depth preference (prefer 2-3)
        depth = genome.get_depth()
        if depth == 2 or depth == 3:
            depth_score = 1.0
        elif depth == 1 or depth == 4:
            depth_score = 0.7
        else:
            depth_score = 0.4

        # Balance (check branching factor consistency)
        children_counts = {}
        for gene in genome.genes:
            parent_id = gene.get('parent_id')
            if parent_id:
                children_counts[parent_id] = children_counts.get(parent_id, 0) + 1

        if children_counts:
            np.mean(list(children_counts.values()))
            std_children = np.std(list(children_counts.values())) if len(children_counts) > 1 else 0
            balance = 1.0 / (1.0 + std_children)
        else:
            balance = 1.0

        # Combine
        fitness = (
            simplicity * weights['simplicity'] +
            depth_score * weights['depth'] +
            balance * weights['balance']
        )

        return min(1.0, max(0.0, fitness))

    evolver = StructureEvolver(config, fitness_evaluator=fitness_evaluator)

    print("\nStarting evolution...")
    print("(Optimizing for simplicity, moderate depth, and balanced structure)\n")

    best_genome = evolver.evolve(target_fitness=0.85)

    # Display results
    print_subsection("Evolution Results")
    print(f"Best Fitness Achieved: {best_genome.fitness:.4f}")
    print("Best Structure:")
    print(f"  - Total Nodes:  {best_genome.get_node_count()}")
    print(f"  - Max Depth:    {best_genome.get_depth()}")
    print(f"  - Generation:   {best_genome.generation}")

    # Show evolution history
    print_subsection("Evolution Progress")
    summary = evolver.get_evolution_summary()
    print(f"Generations Run:      {summary['generations_run']}")
    print(f"Final Best Fitness:   {summary['final_best_fitness']:.4f}")
    print(f"Final Avg Fitness:    {summary['final_avg_fitness']:.4f}")
    print(f"Fitness Improvement:  {summary['fitness_improvement']:.4f}")
    print(f"Convergence Speed:    {summary['convergence_speed']:.4f}")

    # Show fitness progression
    print_subsection("Fitness Progression")
    history = evolver.history
    if history:
        sample_generations = [0, len(history)//4, len(history)//2, 3*len(history)//4, len(history)-1]
        for gen_idx in sample_generations:
            if gen_idx < len(history):
                gen = history[gen_idx]
                print(f"  Gen {gen['generation']:2d}: best={gen['best_fitness']:.3f}, "
                      f"avg={gen['avg_fitness']:.3f}")

    return evolver, best_genome


# ============================================================================
# Example 4: End-to-End Workflow
# ============================================================================

def example_4_end_to_end_workflow():
    """
    Complete workflow combining all Phase 3 components:
    1. Record structure performance
    2. Learn patterns and templates
    3. Evolve structures for optimization
    4. Get recommendations and make decisions
    """
    print_section("Example 4: End-to-End Optimization Workflow")

    # Step 1: Record historical performance
    print_subsection("Step 1: Recording Historical Performance")
    optimizer = FitnessLandscapeOptimizer(memory_size=50)

    print("Recording 24 structure performances...")
    recorded_count = 0

    for task_type in ["research", "analysis"]:
        for complexity in [0.4, 0.7]:
            for i in range(3):
                structure = create_mock_structure(
                    structure_id=f"{task_type}_{i}",
                    task_type=task_type,
                    total_nodes=4 + i,
                    max_depth=2 + (1 if complexity > 0.6 else 0),
                    fitness=0.65 + complexity * 0.2 + random.random() * 0.05
                )

                optimizer.record_structure_performance(
                    root=structure,
                    task_type=task_type,
                    task_complexity=complexity
                )
                recorded_count += 1

    print(f"✓ Recorded {recorded_count} structure performances")

    # Step 2: Learn templates from successful structures
    print_subsection("Step 2: Learning Templates")

    manager = TemplateManager(min_fitness_for_template=0.7, min_usage_for_template=2)

    learned_templates = 0
    for task_type in ["research", "analysis"]:
        snapshots = [s for s in optimizer.snapshots if s.task_type == task_type]
        if snapshots:
            template = manager.learn_from_snapshots(snapshots, task_type)
            if template:
                learned_templates += 1
                print(f"✓ Learned template for '{task_type}' "
                      f"(fitness={template.avg_fitness:.2f})")

    # Step 3: Evolve structures for a specific optimization goal
    print_subsection("Step 3: Evolving Structures for Optimization")

    config = EvolutionConfig(
        population_size=15,
        generations=10,
        mutation_rate=0.35,
        crossover_rate=0.7,
        max_structure_depth=3,
        max_structure_nodes=12
    )

    evolver = StructureEvolver(config)
    best = evolver.evolve(target_fitness=0.8)

    print("✓ Evolution complete")
    print(f"  Best fitness achieved: {best.fitness:.2f}")
    print(f"  Structure: {best.get_node_count()} nodes, depth={best.get_depth()}")

    # Step 4: Make recommendations based on learnings
    print_subsection("Step 4: Making Recommendations")

    test_tasks = [
        ("research", "Research new market trends", 0.6),
        ("analysis", "Analyze user behavior patterns", 0.65)
    ]

    for task_type, description, complexity in test_tasks:
        # Get landscape recommendation
        landscape_rec = optimizer.recommend_structure(task_type, complexity)

        # Get template recommendation
        template_rec = manager.recommend_template(task_type, description)

        print(f"\nTask: {task_type} (complexity={complexity:.2f})")

        if landscape_rec:
            print("  Landscape Recommendation:")
            print(f"    - Optimal Depth:  {landscape_rec.recommended_depth}")
            print(f"    - Optimal Branching: {landscape_rec.recommended_branching:.1f}")
            print(f"    - Confidence: {landscape_rec.confidence:.2f}")

        if template_rec:
            print("  Template Recommendation:")
            print(f"    - Name: {template_rec.name}")
            print(f"    - Type: {template_rec.topology_type}")
            print(f"    - Expected Fitness: {template_rec.avg_fitness:.2f}")

    # Final summary
    print_subsection("Workflow Summary")
    print(f"Total Snapshots Recorded: {len(optimizer.snapshots)}")
    print(f"Templates Learned:        {len(manager.templates)}")
    print(f"Generations Evolved:      {len(evolver.history)}")
    print(f"Best Evolved Fitness:     {best.fitness:.3f}")

    return optimizer, manager, evolver


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "PHASE 3: LANDSCAPE EVOLUTION DEMO" + " " * 20 + "║")
    print("║" + " " * 12 + "Demonstrating Structure Optimization and Learning" + " " * 6 + "║")
    print("╚" + "═" * 68 + "╝")

    # Run examples
    try:
        # Example 1: Landscape analysis
        optimizer = example_1_fitness_landscape()

        # Example 2: Template learning
        manager = example_2_template_learning_and_recommendation(optimizer)

        # Example 3: Structure evolution
        evolver, best_genome = example_3_structure_evolution()

        # Example 4: Complete workflow
        opt, mgr, ev = example_4_end_to_end_workflow()

        # Final summary
        print_section("Demo Complete!")
        print("""
This demo demonstrated the complete Phase 3 capabilities:

1. **Fitness Landscape Optimizer**
   - Records structure performance across different task types
   - Visualizes performance landscape
   - Analyzes patterns and recommends configurations

2. **Template Manager**
   - Learns optimal templates from historical data
   - Provides fast recommendations for new tasks
   - Tracks usage and confidence metrics

3. **Structure Evolution**
   - Uses genetic algorithms for structure optimization
   - Evolves populations through mutation, crossover, selection
   - Finds near-optimal configurations automatically

4. **Integration**
   - Combine all systems for comprehensive optimization
   - Learn from history, evolve for improvement
   - Make intelligent recommendations

Next steps:
- Integrate with Phase 1 and 2 for complete fractal node system
- Use recommendations to guide structure growth decisions
- Continuously improve as more performance data is collected
""")

    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70 + "\n")
