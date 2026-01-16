"""
Fractal Node System - Comprehensive Demo

This example demonstrates all three ways to use the fractal node system:
1. Automatic fractal mode (System 2 triggered)
2. Manual pipeline building
3. Hybrid approach (manual + auto-growth)
"""

import asyncio

from loom.config.fractal import FractalConfig, GrowthTrigger
from loom.llm.openai import OpenAIProvider
from loom.memory.core import LoomMemory
from loom.node import (
    FractalAgentNode,
    PipelineTemplate,
    add_fractal_to_agent,
    build_pipeline,
    create_fractal_agent,
)

# ============================================================================
# Example 1: Automatic Fractal Mode (System 2 Integration)
# ============================================================================

async def example1_auto_fractal():
    """
    Demonstrates automatic fractal decomposition triggered by System 2
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Automatic Fractal Mode (System 2 Triggered)")
    print("="*70 + "\n")

    # Create LLM provider
    llm = OpenAIProvider(model="gpt-4")
    memory = LoomMemory(node_id="auto_fractal")

    # Create fractal agent with System 2 trigger
    agent = await create_fractal_agent(
        node_id="auto_agent",
        llm=llm,
        memory=memory,
        enable_fractal=True,
        fractal_trigger=GrowthTrigger.COMPLEXITY,  # Trigger on complexity
        max_depth=3,
        max_children=4,
        complexity_threshold=0.6
    )

    print("✅ Created auto-fractal agent")
    print(f"   Trigger: {agent.fractal_config.growth_trigger.value}")
    print(f"   Max depth: {agent.fractal_config.max_depth}")
    print(f"   Max children: {agent.fractal_config.max_children}\n")

    # Simple task (won't trigger fractal)
    print("📝 Task 1 (Simple): What is 2 + 2?\n")
    result1 = await agent.execute("What is 2 + 2?")

    print(f"Result: {result1.get('result', 'N/A')}")
    print(f"Structure used: {'Fractal' if result1.get('structure') else 'Direct'}")
    print(f"Execution time: {result1.get('execution_time', 0):.2f}s\n")

    # Complex task (will trigger fractal)
    print("📝 Task 2 (Complex): Multi-step research task\n")
    complex_task = """
    Research the latest developments in quantum computing, analyze their
    impact on cryptography, machine learning, and drug discovery, then
    synthesize findings into a comprehensive report with actionable
    recommendations for each field.
    """

    result2 = await agent.execute(complex_task.strip())

    print(f"Result preview: {str(result2.get('result', ''))[:200]}...")
    print(f"Structure used: {'Fractal' if result2.get('structure') else 'Direct'}")
    print(f"Execution time: {result2.get('execution_time', 0):.2f}s")

    if result2.get('structure'):
        print("\n🌲 Generated Structure:")
        print(agent.visualize_structure())

    # Get statistics
    stats = agent.get_activation_stats() if hasattr(agent, 'get_activation_stats') else {}
    if stats:
        print("\n📊 Statistics:")
        print(f"   System 2 activations: {stats.get('system2_activations', 0)}")
        print(f"   Fractal activations: {stats.get('fractal_activations', 0)}")
        print(f"   Total tasks: {stats.get('total_tasks', 0)}")


# ============================================================================
# Example 2: Manual Pipeline Building
# ============================================================================

async def example2_manual_pipeline():
    """
    Demonstrates manual pipeline construction using the builder API
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Manual Pipeline Building")
    print("="*70 + "\n")

    llm = OpenAIProvider(model="gpt-4")
    memory = LoomMemory(node_id="manual_pipeline")

    # Build a research pipeline using fluent API
    pipeline = (
        build_pipeline("research_pipeline", llm, memory)
        .coordinator("orchestrator")
        .parallel([
            ("ai_research", "specialist"),
            ("market_research", "specialist"),
            ("tech_research", "specialist")
        ], join_with_aggregator=True)
        .build()
    )

    print("✅ Created manual pipeline")
    print("\n🌲 Pipeline Structure:")
    print(pipeline.visualize_structure())

    # Execute task
    print("\n📝 Task: Analyze AI startups landscape\n")

    # Manually assign subtasks to children
    subtasks = [
        "Research recent AI startup funding trends",
        "Analyze market size and growth projections",
        "Identify key technology trends in AI startups"
    ]

    result = await pipeline.execute_pipeline(subtasks, mode="parallel")

    print(f"✅ Executed {len(result)} parallel tasks")
    for i, res in enumerate(result):
        print(f"   Task {i+1}: {res.get('execution_time', 0):.2f}s")


# ============================================================================
# Example 3: Using Templates
# ============================================================================

async def example3_templates():
    """
    Demonstrates using pre-built pipeline templates
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Using Pipeline Templates")
    print("="*70 + "\n")

    llm = OpenAIProvider(model="gpt-4")
    memory = LoomMemory(node_id="template_pipeline")

    # Template 1: Sequential Pipeline
    print("📋 Creating sequential pipeline...\n")
    seq_pipeline = PipelineTemplate.sequential_pipeline(
        name="analysis",
        llm=llm,
        steps=["gather_data", "analyze", "synthesize"],
        memory=memory
    )

    print("✅ Sequential Pipeline:")
    print(seq_pipeline.visualize_structure())

    # Template 2: Research Pipeline
    print("\n📋 Creating research pipeline...\n")
    research_pipeline = PipelineTemplate.research_pipeline(
        name="research",
        llm=llm,
        domains=["healthcare", "finance", "education"],
        memory=memory
    )

    print("✅ Research Pipeline:")
    print(research_pipeline.visualize_structure())

    # Template 3: Iterative Refinement
    print("\n📋 Creating iterative refinement pipeline...\n")
    iterative_pipeline = PipelineTemplate.iterative_refinement(
        name="refinement",
        llm=llm,
        iterations=3,
        memory=memory
    )

    print("✅ Iterative Pipeline:")
    print(iterative_pipeline.visualize_structure())


# ============================================================================
# Example 4: Hybrid Approach (Manual + Auto-Growth)
# ============================================================================

async def example4_hybrid():
    """
    Demonstrates hybrid approach: manual base + auto-growth
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Hybrid Approach (Manual + Auto-Growth)")
    print("="*70 + "\n")

    llm = OpenAIProvider(model="gpt-4")
    memory = LoomMemory(node_id="hybrid")

    # Create manual base structure with auto-growth enabled
    config = FractalConfig(
        enabled=True,
        growth_trigger=GrowthTrigger.ALWAYS,  # Auto-grow when complexity is high
        max_depth=4,
        complexity_threshold=0.5
    )

    pipeline = (
        build_pipeline("hybrid_pipeline", llm, memory)
        .coordinator("main")
        .executor("researcher")
        .executor("analyzer")
        .aggregator("synthesizer")
        .build()
    )

    # Enable auto-growth on specific nodes
    pipeline.children[0].fractal_config = config  # Enable on researcher
    pipeline.children[1].fractal_config = config  # Enable on analyzer

    print("✅ Created hybrid pipeline (manual base + auto-growth on nodes)")
    print("\n🌲 Initial Structure:")
    print(pipeline.visualize_structure())

    print("\n📝 Executing complex task that may trigger growth...\n")

    # Execute - complex subtasks may trigger auto-growth
    subtasks = [
        "Research quantum computing developments (comprehensive analysis across 5 dimensions)",
        "Analyze market impact with statistical modeling and trend forecasting"
    ]

    await pipeline.execute_pipeline(subtasks, mode="sequential")

    print("\n🌲 Final Structure (after execution):")
    print(pipeline.visualize_structure())


# ============================================================================
# Example 5: Runtime Enhancement
# ============================================================================

async def example5_runtime_enhancement():
    """
    Demonstrates adding fractal capabilities to existing agent at runtime
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Runtime Enhancement (Add Fractal to Existing Agent)")
    print("="*70 + "\n")

    llm = OpenAIProvider(model="gpt-4")

    # Create standard FractalAgentNode without fractal mode
    agent = FractalAgentNode(
        node_id="standard_agent",
        llm=llm,
        fractal_config=FractalConfig(enabled=False)
    )

    print("✅ Created standard agent (fractal disabled)")
    print(f"   Fractal enabled: {agent.fractal_config.enabled}\n")

    # Add fractal capabilities at runtime
    add_fractal_to_agent(
        agent,
        enable=True,
        growth_trigger=GrowthTrigger.COMPLEXITY,
        max_depth=3
    )

    print("✅ Enhanced agent with fractal capabilities")
    print(f"   Fractal enabled: {agent.is_fractal_enabled()}")
    print(f"   Trigger: {agent.get_fractal_config().growth_trigger.value}\n")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print(" " * 15 + "FRACTAL NODE SYSTEM - DEMO")
    print("="*70)

    # Run examples
    await example1_auto_fractal()
    await example2_manual_pipeline()
    await example3_templates()
    await example4_hybrid()
    await example5_runtime_enhancement()

    print("\n" + "="*70)
    print(" " * 20 + "ALL EXAMPLES COMPLETED")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
