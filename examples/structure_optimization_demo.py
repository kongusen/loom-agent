"""
Structure Optimization Demo - Phase 2

Demonstrates intelligent structure control, pruning, and health assessment.
"""

import asyncio
from unittest.mock import Mock, AsyncMock

from loom.config.fractal import FractalConfig, NodeRole, GrowthTrigger, GrowthStrategy
from loom.node.fractal import FractalAgentNode
from loom.kernel import (
    StructureController,
    SmartPruner,
    StructureHealthAssessor,
    CompositePruningStrategy,
    FitnessPruningStrategy
)


# ============================================================================
# Example 1: Structure Controller
# ============================================================================

async def example1_structure_controller():
    """Demonstrates StructureController for growth/pruning decisions"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Structure Controller")
    print("="*70 + "\n")

    # Setup
    config = FractalConfig(
        enabled=True,
        max_depth=3,
        max_children=4,
        complexity_threshold=0.6
    )

    controller = StructureController(config)

    # Create mock LLM
    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value="Test response")

    # Create a test node
    node = FractalAgentNode(
        node_id="test_node",
        provider=mock_llm,
        role=NodeRole.COORDINATOR,
        fractal_config=config,
        standalone=True
    )

    print("✅ Created structure controller and test node\n")

    # Test 1: Growth decision for high complexity
    print("📊 Test 1: Should grow with high complexity?")
    should_grow = controller.should_grow(
        node,
        task_complexity=0.8,
        current_confidence=0.5
    )
    print(f"   Task complexity: 0.8, Confidence: 0.5")
    print(f"   Decision: {'GROW ✅' if should_grow else 'DO NOT GROW ❌'}\n")

    # Test 2: Growth decision for low complexity
    print("📊 Test 2: Should grow with low complexity?")
    should_grow2 = controller.should_grow(
        node,
        task_complexity=0.3,
        current_confidence=0.9
    )
    print(f"   Task complexity: 0.3, Confidence: 0.9")
    print(f"   Decision: {'GROW ✅' if should_grow2 else 'DO NOT GROW ❌'}\n")

    # Test 3: Choose growth strategy
    print("🎯 Test 3: Choose growth strategy")
    tasks = [
        "First do step 1, then step 2, finally step 3",
        "Run these tasks in parallel",
        "We need domain experts for this",
        "Iterate and refine the solution"
    ]

    for task in tasks:
        strategy = controller.choose_growth_strategy(node, task)
        print(f"   Task: \"{task[:40]}...\"")
        print(f"   Strategy: {strategy.value}\n")

    # Test 4: Record events
    print("📝 Test 4: Record growth event")
    controller.record_growth(
        node,
        GrowthStrategy.DECOMPOSE,
        children_count=3,
        fitness_before=0.7
    )
    print(f"   Growth events recorded: {controller.stats.total_growth_events}")
    print(f"   History entries: {len(controller.history)}\n")


# ============================================================================
# Example 2: Smart Pruning
# ============================================================================

async def example2_smart_pruning():
    """Demonstrates intelligent pruning with SmartPruner"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Smart Pruning")
    print("="*70 + "\n")

    # Setup
    config = FractalConfig(
        enabled=True,
        pruning_threshold=0.4,
        min_tasks_before_pruning=2
    )

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value="Test response")

    # Create a tree with varying performance
    print("🌳 Creating test tree with varying node performance...\n")

    root = FractalAgentNode(
        node_id="root",
        provider=mock_llm,
        role=NodeRole.COORDINATOR,
        fractal_config=config,
        standalone=True
    )

    # Add children with different performance profiles
    performances = [
        ("high_performer", 5, 5, 1000),   # 100% success, low tokens
        ("low_performer", 5, 1, 8000),    # 20% success, high tokens
        ("avg_performer", 5, 3, 3000),    # 60% success, medium tokens
        ("new_node", 1, 1, 500)           # Too few tasks to judge
    ]

    for name, tasks, successes, tokens in performances:
        child = FractalAgentNode(
            node_id=name,
            provider=mock_llm,
            role=NodeRole.EXECUTOR,
            parent=root,
            depth=1,
            fractal_config=config,
            standalone=True
        )

        # Simulate task history
        for i in range(tasks):
            child.metrics.record_execution(
                success=(i < successes),
                tokens=tokens,
                time=1.0
            )

        root.children.append(child)

    print("Nodes created:")
    for child in root.children:
        fitness = child.metrics.fitness_score() if child.metrics.task_count > 0 else 0
        print(f"  • {child.node_id}: "
              f"tasks={child.metrics.task_count}, "
              f"success={child.metrics.success_rate:.1%}, "
              f"fitness={fitness:.2f}")
    print()

    # Prune with different strategies
    print("🔍 Strategy 1: Fitness-based pruning (dry run)")
    strategy1 = FitnessPruningStrategy(fitness_threshold=0.5, min_tasks=2)
    pruner1 = SmartPruner(strategy=strategy1, dry_run=True)
    report1 = pruner1.prune_structure(root)

    print(f"   Nodes to prune: {report1['pruned_count']}")
    if report1['pruned_nodes']:
        print(f"   Candidates: {', '.join(report1['pruned_nodes'])}")
    print()

    print("🔍 Strategy 2: Composite pruning (dry run)")
    strategy2 = CompositePruningStrategy()
    pruner2 = SmartPruner(strategy=strategy2, dry_run=True)
    report2 = pruner2.prune_structure(root)

    print(f"   Nodes to prune: {report2['pruned_count']}")
    if report2['pruned_nodes']:
        print(f"   Candidates: {', '.join(report2['pruned_nodes'])}")
    print()

    # Show evaluations
    print("📋 Detailed evaluations:")
    for node_id, decision in pruner2.get_all_evaluations().items():
        print(f"   {node_id}:")
        print(f"     Should prune: {decision.should_prune}")
        print(f"     Confidence: {decision.confidence:.2f}")
        print(f"     Reason: {decision.reason}")
    print()


# ============================================================================
# Example 3: Health Assessment
# ============================================================================

async def example3_health_assessment():
    """Demonstrates structure health assessment"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Health Assessment")
    print("="*70 + "\n")

    # Setup
    config = FractalConfig(enabled=True, max_depth=3)
    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value="Test response")

    # Create two structures: healthy and unhealthy

    # Structure 1: Healthy (balanced, good performance)
    print("🟢 Creating healthy structure...\n")
    healthy_root = FractalAgentNode(
        node_id="healthy_root",
        provider=mock_llm,
        role=NodeRole.COORDINATOR,
        fractal_config=config,
        standalone=True
    )

    for i in range(3):
        child = FractalAgentNode(
            node_id=f"healthy.{i}",
            provider=mock_llm,
            role=NodeRole.EXECUTOR,
            parent=healthy_root,
            depth=1,
            fractal_config=config,
            standalone=True
        )

        # Good performance
        for j in range(5):
            child.metrics.record_execution(
                success=True,
                tokens=2000,
                time=1.0
            )

        healthy_root.children.append(child)

    # Structure 2: Unhealthy (unbalanced, poor performance)
    print("🔴 Creating unhealthy structure...\n")
    unhealthy_root = FractalAgentNode(
        node_id="unhealthy_root",
        provider=mock_llm,
        role=NodeRole.COORDINATOR,
        fractal_config=config,
        standalone=True
    )

    # Add performing children
    for i in range(2):
        child = FractalAgentNode(
            node_id=f"unhealthy.good.{i}",
            provider=mock_llm,
            role=NodeRole.EXECUTOR,
            parent=unhealthy_root,
            depth=1,
            fractal_config=config,
            standalone=True
        )

        for j in range(5):
            child.metrics.record_execution(success=True, tokens=2000, time=1.0)

        unhealthy_root.children.append(child)

    # Add idle children (no tasks)
    for i in range(8):
        idle_child = FractalAgentNode(
            node_id=f"unhealthy.idle.{i}",
            provider=mock_llm,
            role=NodeRole.EXECUTOR,
            parent=unhealthy_root,
            depth=1,
            fractal_config=config,
            standalone=True
        )
        unhealthy_root.children.append(idle_child)

    # Add deep inefficient branch
    deep_child = FractalAgentNode(
        node_id="unhealthy.deep",
        provider=mock_llm,
        parent=unhealthy_root,
        depth=1,
        fractal_config=config,
        standalone=True
    )
    for j in range(5):
        deep_child.metrics.record_execution(success=False, tokens=10000, time=20.0)
    unhealthy_root.children.append(deep_child)

    # Assess both structures
    assessor = StructureHealthAssessor()

    print("📊 Assessing healthy structure...")
    healthy_report = assessor.assess(healthy_root, config)
    print(assessor.format_report(healthy_report))

    print("\n📊 Assessing unhealthy structure...")
    unhealthy_report = assessor.assess(unhealthy_root, config)
    print(assessor.format_report(unhealthy_report))


# ============================================================================
# Example 4: Complete Workflow
# ============================================================================

async def example4_complete_workflow():
    """Demonstrates complete optimization workflow"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Complete Optimization Workflow")
    print("="*70 + "\n")

    # Setup
    config = FractalConfig(
        enabled=True,
        max_depth=3,
        complexity_threshold=0.6,
        pruning_threshold=0.4
    )

    controller = StructureController(config)
    assessor = StructureHealthAssessor()
    pruner = SmartPruner(dry_run=False)  # Actual pruning

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value="Test response")

    # Create initial structure
    print("1️⃣ Creating initial structure...\n")
    root = FractalAgentNode(
        node_id="workflow_root",
        provider=mock_llm,
        role=NodeRole.COORDINATOR,
        fractal_config=config,
        standalone=True
    )

    # Add mixed-performance children
    for i in range(5):
        child = FractalAgentNode(
            node_id=f"workflow.{i}",
            provider=mock_llm,
            parent=root,
            depth=1,
            fractal_config=config,
            standalone=True
        )

        # Varying performance
        if i < 2:  # Good performers
            for j in range(5):
                child.metrics.record_execution(True, 2000, 1.0)
        elif i < 4:  # Poor performers
            for j in range(5):
                child.metrics.record_execution(False, 8000, 10.0)
        # else: Idle (no tasks)

        root.children.append(child)

    print(f"   Created structure with {len(root.children)} children\n")

    # Step 2: Assess health
    print("2️⃣ Assessing initial health...\n")
    initial_health = assessor.assess(root, config)
    print(f"   Overall Score: {initial_health.overall_score:.2f}")
    print(f"   Status: {initial_health.status.value}")
    print(f"   Issues Found: {len(initial_health.diagnostics)}\n")

    # Step 3: Identify problems
    print("3️⃣ Identifying inefficient nodes...\n")
    inefficient = controller.get_inefficient_nodes(root)
    print(f"   Found {len(inefficient)} inefficient nodes:")
    for node, fitness, reason in inefficient:
        print(f"     • {node.node_id}: fitness={fitness:.2f}, {reason}")
    print()

    # Step 4: Prune
    print("4️⃣ Pruning inefficient nodes...\n")
    prune_report = pruner.prune_structure(root)
    print(f"   Nodes before: {prune_report['nodes_before']}")
    print(f"   Nodes pruned: {prune_report['pruned_count']}")
    print(f"   Nodes after: {prune_report['nodes_after']}")
    if prune_report['pruned_nodes']:
        print(f"   Removed: {', '.join(prune_report['pruned_nodes'])}")
    print()

    # Step 5: Re-assess
    print("5️⃣ Re-assessing after pruning...\n")
    final_health = assessor.assess(root, config)
    print(f"   Overall Score: {final_health.overall_score:.2f} "
          f"({'↑' if final_health.overall_score > initial_health.overall_score else '↓'} "
          f"{abs(final_health.overall_score - initial_health.overall_score):.2f})")
    print(f"   Status: {final_health.status.value}")
    print(f"   Issues Found: {len(final_health.diagnostics)}\n")

    # Summary
    print("📊 Summary:")
    print(f"   Health improvement: {final_health.overall_score - initial_health.overall_score:+.2f}")
    print(f"   Nodes reduced: {prune_report['nodes_before']} → {prune_report['nodes_after']}")
    print(f"   Issues reduced: {len(initial_health.diagnostics)} → {len(final_health.diagnostics)}")
    print()


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print(" " * 15 + "STRUCTURE OPTIMIZATION - DEMO")
    print("="*70)

    await example1_structure_controller()
    await example2_smart_pruning()
    await example3_health_assessment()
    await example4_complete_workflow()

    print("\n" + "="*70)
    print(" " * 20 + "ALL EXAMPLES COMPLETED")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
