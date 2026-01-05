"""
Complete Demo: LoomMemory Optimization Features

This example demonstrates all the optimization features:
1. Vector Store Integration (Pluggable)
2. Embedding Provider (Pluggable)
3. System 1/2 Routing with Confidence Estimation
4. Memory Compression
5. Performance Metrics & Visualization
"""
import asyncio
from loom.memory.core import LoomMemory
from loom.memory.config import MemoryConfig, VectorStoreConfig, EmbeddingConfig
from loom.memory.types import MemoryUnit, MemoryTier, MemoryType
from loom.memory.compression import MemoryCompressor
from loom.memory.metrics import MetricsCollector
from loom.memory.visualizer import MetricsVisualizer
from loom.node.agent import AgentNode
from loom.kernel.core import Dispatcher


async def demo_vector_store_configuration():
    """Demo 1: Configuring Vector Store"""
    print("=" * 60)
    print("DEMO 1: Vector Store Configuration")
    print("=" * 60)

    # Option 1: In-Memory (Default, for development)
    config_inmemory = MemoryConfig(
        vector_store=VectorStoreConfig(
            provider="inmemory",
            enabled=True
        ),
        embedding=EmbeddingConfig(
            provider="mock"  # Use mock for testing
        )
    )

    # Option 2: Qdrant (Production)
    config_qdrant = MemoryConfig(
        vector_store=VectorStoreConfig(
            provider="qdrant",
            enabled=True,
            provider_config={
                "url": "http://localhost:6333",
                "collection_name": "loom_memory",
                "vector_size": 1536
            }
        ),
        embedding=EmbeddingConfig(
            provider="openai",
            enable_cache=True,
            provider_config={
                "api_key": "sk-...",  # Your API key
                "model": "text-embedding-3-small"
            }
        )
    )

    # Option 3: ChromaDB (Alternative)
    config_chroma = MemoryConfig(
        vector_store=VectorStoreConfig(
            provider="chroma",
            enabled=True,
            provider_config={
                "persist_directory": "./chroma_db",
                "collection_name": "loom_memory"
            }
        ),
        embedding=EmbeddingConfig(
            provider="openai",
            enable_cache=True,
            provider_config={
                "api_key": "sk-...",
                "model": "text-embedding-3-small"
            }
        )
    )

    # Create memory with configuration
    memory = LoomMemory(node_id="demo_node", config=config_inmemory)

    # Add some L4 facts (will be auto-vectorized)
    fact1 = MemoryUnit(
        content="The company was founded in 2020",
        tier=MemoryTier.L4_GLOBAL,
        type=MemoryType.FACT,
        importance=0.9
    )

    fact2 = MemoryUnit(
        content="Our main product is an AI agent framework",
        tier=MemoryTier.L4_GLOBAL,
        type=MemoryType.FACT,
        importance=0.9
    )

    await memory.add(fact1)
    await memory.add(fact2)

    print(f"✅ Added {len(memory._l4_global)} facts to L4")
    print(f"✅ Vector store enabled: {memory.vector_store is not None}")
    print(f"✅ Embedding provider: {type(memory.embedding_provider).__name__}")
    print()


async def demo_system1_system2_routing():
    """Demo 2: System 1/2 Routing with Confidence"""
    print("=" * 60)
    print("DEMO 2: System 1/2 Routing")
    print("=" * 60)

    # Create dispatcher and agent
    dispatcher = Dispatcher()

    # Agent with System 1/2 routing enabled
    agent = AgentNode(
        node_id="routing_demo",
        dispatcher=dispatcher,
        system_prompt="You are a helpful assistant."
    )

    # Test queries
    test_queries = [
        ("What is 2+2?", "SYSTEM_1"),  # Simple, should use S1
        ("Explain quantum computing in detail", "SYSTEM_2"),  # Complex, should use S2
        ("What's the capital of France?", "SYSTEM_1"),  # Factual, should use S1
    ]

    for query, expected_system in test_queries:
        print(f"\n📝 Query: {query}")

        # Classify
        decision = agent.classifier.classify(query)
        print(f"   Routing: {decision.system.value}")
        print(f"   Confidence: {decision.confidence:.2f}")
        print(f"   Reasoning: {decision.reasoning}")
        print(f"   Expected: {expected_system}")
        print(f"   Match: {'✅' if decision.system.value.upper() == expected_system else '❌'}")

    print()


async def demo_memory_compression():
    """Demo 3: Memory Compression"""
    print("=" * 60)
    print("DEMO 3: Memory Compression")
    print("=" * 60)

    memory = LoomMemory(node_id="compression_demo")
    compressor = MemoryCompressor(
        llm_provider=None,  # Use simple compression
        l1_to_l3_threshold=5
    )

    # Add many L1 messages
    for i in range(10):
        unit = MemoryUnit(
            content=f"User message {i}",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE
        )
        await memory.add(unit)

    print(f"✅ Added {len(memory._l1_buffer)} messages to L1")

    # Compress L1 to L3
    summary_id = await compressor.compress_l1_to_l3(memory)

    if summary_id:
        print(f"✅ Created L3 summary: {summary_id}")
        summary = memory.get(summary_id)
        print(f"   Content: {summary.content}")

    # Add some L2 plans
    plan = MemoryUnit(
        content="Analyze Q3 sales data",
        tier=MemoryTier.L2_WORKING,
        type=MemoryType.PLAN,
        importance=0.9
    )
    await memory.add(plan)

    # Extract facts to L4
    fact_ids = await compressor.extract_facts_to_l4(memory)
    print(f"✅ Extracted {len(fact_ids)} facts to L4")

    print()


async def demo_performance_metrics():
    """Demo 4: Performance Metrics & Visualization"""
    print("=" * 60)
    print("DEMO 4: Performance Metrics")
    print("=" * 60)

    # Create metrics collector
    collector = MetricsCollector()
    visualizer = MetricsVisualizer(collector)

    # Simulate some operations
    collector.record_memory_add("L1")
    collector.record_memory_add("L2")
    collector.record_memory_add("L4")
    collector.update_memory_sizes(l1=10, l2=5, l3=3, l4=2)

    collector.record_routing_decision("system_1")
    collector.record_routing_decision("system_1")
    collector.record_routing_decision("system_2")

    collector.record_s1_execution(
        duration_ms=150,
        tokens=50,
        confidence=0.85,
        success=True
    )

    collector.record_s2_execution(
        duration_ms=2500,
        tokens=3000,
        iterations=3
    )

    collector.record_token_savings(2950)

    collector.record_context_assembly(
        duration_ms=50,
        tokens=500,
        units_curated=20,
        units_selected=10
    )

    # Render visualizations
    print(visualizer.render_memory_status())
    print(visualizer.render_routing_performance())
    print(visualizer.render_context_performance())

    # Compact summary
    print("\n📊 Compact Summary:")
    print(visualizer.render_compact_summary())
    print()


async def demo_complete_workflow():
    """Demo 5: Complete Workflow"""
    print("=" * 60)
    print("DEMO 5: Complete Workflow")
    print("=" * 60)

    # 1. Configure memory with all features
    config = MemoryConfig(
        max_l1_size=50,
        vector_store=VectorStoreConfig(
            provider="inmemory",
            enabled=True
        ),
        embedding=EmbeddingConfig(
            provider="mock",
            enable_cache=True
        ),
        auto_vectorize_l4=True,
        enable_auto_compression=True,
        l1_to_l3_threshold=30
    )

    memory = LoomMemory(node_id="complete_demo", config=config)

    # 2. Add various types of memories
    print("📝 Adding memories...")

    # L1: Recent interactions
    for i in range(5):
        await memory.add(MemoryUnit(
            content=f"User: Question {i}",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE
        ))

    # L2: Working memory
    await memory.add(MemoryUnit(
        content="Current task: Analyze data",
        tier=MemoryTier.L2_WORKING,
        type=MemoryType.PLAN,
        importance=1.0
    ))

    # L4: Global facts (auto-vectorized)
    await memory.add(MemoryUnit(
        content="Company revenue: $10M",
        tier=MemoryTier.L4_GLOBAL,
        type=MemoryType.FACT,
        importance=0.9
    ))

    # 3. Query with semantic search
    from loom.memory.types import MemoryQuery

    results = await memory.query(MemoryQuery(
        tiers=[MemoryTier.L4_GLOBAL],
        query_text="revenue",
        top_k=5
    ))

    print(f"✅ Found {len(results)} relevant facts")

    # 4. Get statistics
    stats = memory.get_statistics()
    print(f"\n📊 Memory Statistics:")
    print(f"   L1: {stats['l1_size']} units")
    print(f"   L2: {stats['l2_size']} units")
    print(f"   L3: {stats['l3_sessions']} sessions")
    print(f"   L4: {stats['l4_size']} units")
    print(f"   Total: {stats['total_units']} units")

    print()


async def main():
    """Run all demos"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     LOOM MEMORY OPTIMIZATION - COMPLETE DEMO             ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    await demo_vector_store_configuration()
    await demo_system1_system2_routing()
    await demo_memory_compression()
    await demo_performance_metrics()
    await demo_complete_workflow()

    print("=" * 60)
    print("✅ All Demos Complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
