"""
Test advanced compression features (Phase 3 completion)
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loom.memory.core import LoomMemory
from loom.config import MemoryConfig
from loom.memory.types import MemoryUnit, MemoryTier, MemoryType, MemoryStatus
from loom.memory.compression import MemoryCompressor


async def test_memory_status_enum():
    """Test 1: MemoryStatus enum"""
    print("\n" + "="*60)
    print("TEST 1: MemoryStatus Enum")
    print("="*60)

    try:
        # Test enum values
        assert MemoryStatus.ACTIVE.value == "active"
        assert MemoryStatus.ARCHIVED.value == "archived"
        assert MemoryStatus.SUMMARIZED.value == "summarized"
        assert MemoryStatus.EVICTED.value == "evicted"

        # Test MemoryUnit with status
        unit = MemoryUnit(
            content="Test message",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE
        )
        assert unit.status == MemoryStatus.ACTIVE

        # Test status change
        unit.status = MemoryStatus.SUMMARIZED
        assert unit.status == MemoryStatus.SUMMARIZED

        print("✅ MemoryStatus enum: PASSED")
        return True
    except Exception as e:
        print(f"❌ MemoryStatus enum: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_compressor_init():
    """Test 2: MemoryCompressor initialization"""
    print("\n" + "="*60)
    print("TEST 2: MemoryCompressor Initialization")
    print("="*60)

    try:
        compressor = MemoryCompressor(
            llm_provider=None,
            l1_to_l3_threshold=30,
            l3_to_l4_threshold=50,
            token_threshold=4000
        )

        assert compressor.l1_to_l3_threshold == 30
        assert compressor.l3_to_l4_threshold == 50
        assert compressor.token_threshold == 4000
        assert compressor.encoder is not None

        print("✅ MemoryCompressor initialization: PASSED")
        return True
    except Exception as e:
        print(f"❌ MemoryCompressor initialization: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_compress_l1_to_l3():
    """Test 3: L1 to L3 compression"""
    print("\n" + "="*60)
    print("TEST 3: L1 to L3 Compression")
    print("="*60)

    try:
        memory = LoomMemory(node_id="test_compress")
        compressor = MemoryCompressor(
            llm_provider=None,
            l1_to_l3_threshold=5,  # Low threshold for testing
            token_threshold=100
        )

        # Add L1 messages
        for i in range(10):
            await memory.add(MemoryUnit(
                content=f"User message {i}: This is a test message with some content.",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE
            ))

        # Compress
        summary_id = await compressor.compress_l1_to_l3(memory)

        assert summary_id is not None, "Should create summary"

        # Verify summary exists
        summary = memory.get(summary_id)
        assert summary is not None
        assert summary.tier == MemoryTier.L3_SESSION
        assert summary.type == MemoryType.SUMMARY

        print(f"✅ L1 to L3 compression: PASSED")
        print(f"   Created summary: {summary.content[:80]}...")
        return True
    except Exception as e:
        print(f"❌ L1 to L3 compression: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_extract_facts_to_l4():
    """Test 4: Extract facts to L4"""
    print("\n" + "="*60)
    print("TEST 4: Extract Facts to L4")
    print("="*60)

    try:
        memory = LoomMemory(node_id="test_facts")
        compressor = MemoryCompressor(
            llm_provider=None,
            l3_to_l4_threshold=3,  # Low threshold for testing
            token_threshold=100
        )

        # Add L2/L3 content with high importance
        for i in range(5):
            await memory.add(MemoryUnit(
                content=f"Important fact {i}: The system uses advanced memory compression.",
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.MESSAGE,
                importance=0.9
            ))

        # Extract facts
        fact_ids = await compressor.extract_facts_to_l4(memory)

        assert len(fact_ids) > 0, "Should extract facts"

        # Verify facts exist in L4
        for fact_id in fact_ids:
            fact = memory.get(fact_id)
            assert fact is not None
            assert fact.tier == MemoryTier.L4_GLOBAL
            assert fact.type == MemoryType.FACT

        print(f"✅ Extract facts to L4: PASSED")
        print(f"   Extracted {len(fact_ids)} facts")
        return True
    except Exception as e:
        print(f"❌ Extract facts to L4: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     ADVANCED COMPRESSION FEATURES - TEST SUITE           ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    tests = [
        test_memory_status_enum,
        test_memory_compressor_init,
        test_compress_l1_to_l3,
        test_extract_facts_to_l4
    ]

    results = []
    for test in tests:
        result = await test()
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
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
