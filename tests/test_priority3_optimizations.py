"""
Test Priority 3 optimizations (Quality Improvements)
"""
import asyncio
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loom.kernel.core import ToolExecutor
from loom.config.execution import ExecutionConfig
from loom.memory.core import LoomMemory
from loom.memory.types import MemoryUnit, MemoryTier, MemoryType


async def test_error_recovery_retry():
    """Test 1: Error recovery with retry"""
    print("\n" + "="*60)
    print("TEST 1: Error Recovery with Retry")
    print("="*60)

    try:
        config = ExecutionConfig()
        executor = ToolExecutor(config)

        # Mock executor that fails first time, succeeds second time
        attempt_count = 0
        async def mock_executor(name, args):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise Exception("Temporary failure")
            return f"Success on attempt {attempt_count}"

        # Execute with retry
        call = {"name": "test_tool", "arguments": {}}
        result = await executor._safe_execute_with_retry(0, call, mock_executor, max_retries=2)

        # Verify retry worked
        assert not result.error, "Should succeed after retry"
        assert attempt_count == 2, f"Expected 2 attempts, got {attempt_count}"

        print("✅ Error recovery with retry: PASSED")
        print(f"   Succeeded after {attempt_count} attempts")
        return True
    except Exception as e:
        print(f"❌ Error recovery with retry: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_call_deduplication():
    """Test 2: Tool call deduplication"""
    print("\n" + "="*60)
    print("TEST 2: Tool Call Deduplication")
    print("="*60)

    try:
        config = ExecutionConfig()
        executor = ToolExecutor(config)

        # Create duplicate tool calls
        tool_calls = [
            {"name": "read_file", "arguments": {"path": "/test.txt"}},
            {"name": "read_file", "arguments": {"path": "/test.txt"}},  # Duplicate
            {"name": "read_file", "arguments": {"path": "/other.txt"}},
            {"name": "read_file", "arguments": {"path": "/test.txt"}},  # Duplicate
        ]

        # Deduplicate
        unique_calls, index_map = executor._deduplicate_calls(tool_calls)

        # Verify deduplication
        assert len(unique_calls) == 2, f"Expected 2 unique calls, got {len(unique_calls)}"
        assert index_map[0] == index_map[1], "Indices 0 and 1 should map to same unique call"
        assert index_map[0] == index_map[3], "Indices 0 and 3 should map to same unique call"
        assert index_map[2] != index_map[0], "Index 2 should map to different unique call"

        print("✅ Tool call deduplication: PASSED")
        print(f"   Reduced {len(tool_calls)} calls to {len(unique_calls)} unique calls")
        return True
    except Exception as e:
        print(f"❌ Tool call deduplication: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_lru_memory_eviction():
    """Test 3: LRU/LFU memory eviction"""
    print("\n" + "="*60)
    print("TEST 3: LRU/LFU Memory Eviction")
    print("="*60)

    try:
        memory = LoomMemory(node_id="test_eviction", max_l1_size=3)

        # Add units with different importance scores
        await memory.add(MemoryUnit(
            content="Low importance, old",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE,
            importance=0.3
        ))
        time.sleep(0.1)  # Small delay to ensure different timestamps

        await memory.add(MemoryUnit(
            content="High importance, recent",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE,
            importance=0.9
        ))

        await memory.add(MemoryUnit(
            content="Medium importance",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE,
            importance=0.5
        ))

        # Add one more to trigger eviction
        await memory.add(MemoryUnit(
            content="New unit",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE,
            importance=0.7
        ))

        # Check that L1 buffer size is maintained
        assert len(memory._l1_buffer) == 3, f"Expected L1 size 3, got {len(memory._l1_buffer)}"

        # Verify that low importance item was evicted
        contents = [u.content for u in memory._l1_buffer]
        assert "Low importance, old" not in contents, "Low importance item should be evicted"
        assert "High importance, recent" in contents, "High importance item should be retained"

        print("✅ LRU/LFU memory eviction: PASSED")
        print(f"   Evicted low-importance item, retained high-importance items")
        return True
    except Exception as e:
        print(f"❌ LRU/LFU memory eviction: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     PRIORITY 3 OPTIMIZATIONS - TEST SUITE               ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    tests = [
        test_error_recovery_retry,
        test_tool_call_deduplication,
        test_lru_memory_eviction
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
