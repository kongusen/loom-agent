"""
Basic tests for memory optimization features
"""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loom.cognition.confidence import ConfidenceEstimator
from loom.config import EmbeddingConfig, MemoryConfig, VectorStoreConfig
from loom.memory.compression import MemoryCompressor
from loom.memory.core import LoomMemory
from loom.memory.metrics import MetricsCollector
from loom.memory.types import MemoryQuery, MemoryTier, MemoryType, MemoryUnit
from loom.memory.visualizer import MetricsVisualizer


async def test_vector_store_config():
    """Test 1: Vector store configuration"""
    print("\n" + "=" * 60)
    print("TEST 1: Vector Store Configuration")
    print("=" * 60)

    try:
        # Test InMemory configuration
        config = MemoryConfig(
            vector_store=VectorStoreConfig(provider="inmemory", enabled=True),
            embedding=EmbeddingConfig(provider="mock"),
        )

        memory = LoomMemory(node_id="test_node", config=config)

        assert memory.vector_store is not None, "Vector store should be initialized"
        assert memory.embedding_provider is not None, "Embedding provider should be initialized"

        print("✅ Vector store configuration: PASSED")
        return True
    except Exception as e:
        print(f"❌ Vector store configuration: FAILED - {e}")
        return False


async def test_auto_vectorization():
    """Test 2: Auto-vectorization of L4 content"""
    print("\n" + "=" * 60)
    print("TEST 2: Auto-Vectorization")
    print("=" * 60)

    try:
        config = MemoryConfig(
            vector_store=VectorStoreConfig(provider="inmemory", enabled=True),
            embedding=EmbeddingConfig(provider="mock"),
            auto_vectorize_l4=True,
        )

        memory = LoomMemory(node_id="test_vectorize", config=config)

        # Add L4 fact
        fact = MemoryUnit(
            content="The company was founded in 2020",
            tier=MemoryTier.L4_GLOBAL,
            type=MemoryType.FACT,
            importance=0.9,
        )

        unit_id = await memory.add(fact)

        # Check if vectorized
        stored_unit = memory.get(unit_id)
        assert stored_unit is not None, "Unit should be stored"
        assert stored_unit.embedding is not None, "Unit should have embedding"

        print(f"✅ Auto-vectorization: PASSED (embedding dim: {len(stored_unit.embedding)})")
        return True
    except Exception as e:
        print(f"❌ Auto-vectorization: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_semantic_search():
    """Test 3: Semantic search"""
    print("\n" + "=" * 60)
    print("TEST 3: Semantic Search")
    print("=" * 60)

    try:
        config = MemoryConfig(
            vector_store=VectorStoreConfig(provider="inmemory", enabled=True),
            embedding=EmbeddingConfig(provider="mock"),
            auto_vectorize_l4=True,
        )

        memory = LoomMemory(node_id="test_search", config=config)

        # Add multiple facts
        facts = [
            "The company was founded in 2020",
            "Our main product is an AI agent framework",
            "We have 50 employees",
        ]

        for fact_text in facts:
            await memory.add(
                MemoryUnit(
                    content=fact_text,
                    tier=MemoryTier.L4_GLOBAL,
                    type=MemoryType.FACT,
                    importance=0.9,
                )
            )

        # Search
        results = await memory.query(
            MemoryQuery(tiers=[MemoryTier.L4_GLOBAL], query_text="company information", top_k=3)
        )

        assert len(results) > 0, "Should find results"
        print(f"✅ Semantic search: PASSED (found {len(results)} results)")
        return True
    except Exception as e:
        print(f"❌ Semantic search: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_confidence_estimation():
    """Test 4: Confidence estimation"""
    print("\n" + "=" * 60)
    print("TEST 4: Confidence Estimation")
    print("=" * 60)

    try:
        estimator = ConfidenceEstimator()

        # Test confident response
        confident_result = estimator.estimate(query="What is 2+2?", response="4")

        # Test uncertain response
        uncertain_result = estimator.estimate(
            query="Explain quantum computing",
            response="Well, quantum computing is complex and I'm not entirely sure, but maybe it involves quantum mechanics and perhaps some advanced physics concepts that are unclear to me.",
        )

        assert (
            confident_result.score >= 0.7
        ), f"Confident response should have high score, got {confident_result.score}"
        assert (
            uncertain_result.score < 0.7
        ), f"Uncertain response should have low score, got {uncertain_result.score}"

        print("✅ Confidence estimation: PASSED")
        print(f"   Confident: {confident_result.score:.2f} - {confident_result.reasoning}")
        print(f"   Uncertain: {uncertain_result.score:.2f} - {uncertain_result.reasoning}")
        return True
    except Exception as e:
        print(f"❌ Confidence estimation: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_memory_compression():
    """Test 5: Memory compression"""
    print("\n" + "=" * 60)
    print("TEST 5: Memory Compression")
    print("=" * 60)

    try:
        memory = LoomMemory(node_id="test_compress")
        compressor = MemoryCompressor(llm_provider=None, l1_to_l3_threshold=5)

        # Add L1 messages
        for i in range(10):
            await memory.add(
                MemoryUnit(
                    content=f"User message {i}", tier=MemoryTier.L1_RAW_IO, type=MemoryType.MESSAGE
                )
            )

        initial_l1_size = len(memory._l1_buffer)

        # Compress
        summary_id = await compressor.compress_l1_to_l3(memory)

        assert summary_id is not None, "Should create summary"

        summary = memory.get(summary_id)
        assert summary.tier == MemoryTier.L3_SESSION, "Summary should be in L3"

        print("✅ Memory compression: PASSED")
        print(f"   Compressed {initial_l1_size} L1 messages to L3 summary")
        return True
    except Exception as e:
        print(f"❌ Memory compression: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_metrics_collection():
    """Test 6: Metrics collection"""
    print("\n" + "=" * 60)
    print("TEST 6: Metrics Collection")
    print("=" * 60)

    try:
        collector = MetricsCollector()
        visualizer = MetricsVisualizer(collector)

        # Record some metrics
        collector.record_memory_add("L1")
        collector.record_memory_add("L4")
        collector.update_memory_sizes(l1=10, l2=5, l3=3, l4=2)

        collector.record_routing_decision("system_1")
        collector.record_s1_execution(duration_ms=150, tokens=50, confidence=0.85, success=True)

        # Get summary
        summary = collector.get_summary()

        assert summary["memory"]["total_memory_units"] == 20, "Should track memory units"
        assert summary["routing"]["s1_calls"] == 1, "Should track S1 calls"

        print("✅ Metrics collection: PASSED")
        print(f"\n{visualizer.render_compact_summary()}")
        return True
    except Exception as e:
        print(f"❌ Metrics collection: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     LOOM MEMORY OPTIMIZATION - TEST SUITE                ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    tests = [
        test_vector_store_config,
        test_auto_vectorization,
        test_semantic_search,
        test_confidence_estimation,
        test_memory_compression,
        test_metrics_collection,
    ]

    results = []
    for test in tests:
        result = await test()
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
