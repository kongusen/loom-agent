"""
Test Priority 2 optimizations (High-Impact features)
"""
import asyncio
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loom.config import ContextConfig
from loom.config.execution import ExecutionConfig
from loom.kernel.core import ToolExecutor
from loom.memory.context import ContextAssembler
from loom.memory.core import LoomMemory
from loom.memory.types import MemoryTier, MemoryType, MemoryUnit


async def test_tool_result_caching():
    """Test 1: Tool result caching"""
    print("\n" + "="*60)
    print("TEST 1: Tool Result Caching")
    print("="*60)

    try:
        config = ExecutionConfig()
        executor = ToolExecutor(config)

        # Mock executor function
        call_count = 0
        async def mock_executor(name, args):
            nonlocal call_count
            call_count += 1
            return f"Result for {name} with {args}"

        # First call - should execute
        call1 = {"name": "read_file", "arguments": {"path": "/test.txt"}}
        result1 = await executor._safe_execute(0, call1, mock_executor)

        # Second call with same args - should use cache
        result2 = await executor._safe_execute(1, call1, mock_executor)

        # Verify caching worked
        assert call_count == 1, f"Expected 1 execution, got {call_count}"
        assert result1.result == result2.result, "Results should match"

        # Different args - should execute again
        call2 = {"name": "read_file", "arguments": {"path": "/other.txt"}}
        await executor._safe_execute(2, call2, mock_executor)
        assert call_count == 2, f"Expected 2 executions, got {call_count}"

        print("✅ Tool result caching: PASSED")
        print("   Cache hit rate: 50% (1 cached, 1 miss)")
        return True
    except Exception as e:
        print(f"❌ Tool result caching: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_ttl_expiration():
    """Test 2: Cache TTL expiration"""
    print("\n" + "="*60)
    print("TEST 2: Cache TTL Expiration")
    print("="*60)

    try:
        config = ExecutionConfig()
        executor = ToolExecutor(config)
        executor.cache_ttl = 0.5  # 0.5 seconds for testing

        call_count = 0
        async def mock_executor(name, args):
            nonlocal call_count
            call_count += 1
            return f"Result {call_count}"

        # First call
        call1 = {"name": "read_file", "arguments": {"path": "/test.txt"}}
        await executor._safe_execute(0, call1, mock_executor)
        assert call_count == 1

        # Immediate second call - should use cache
        await executor._safe_execute(1, call1, mock_executor)
        assert call_count == 1, "Should use cache"

        # Wait for TTL to expire
        time.sleep(0.6)

        # Third call after TTL - should execute again
        await executor._safe_execute(2, call1, mock_executor)
        assert call_count == 2, "Cache should have expired"

        print("✅ Cache TTL expiration: PASSED")
        print(f"   Cache expired after {executor.cache_ttl}s as expected")
        return True
    except Exception as e:
        print(f"❌ Cache TTL expiration: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_adaptive_token_budgeting():
    """Test 3: Adaptive token budgeting"""
    print("\n" + "="*60)
    print("TEST 3: Adaptive Token Budgeting")
    print("="*60)

    try:
        memory = LoomMemory(node_id="test_budget")
        config = ContextConfig()
        assembler = ContextAssembler(config)

        # Test 1: Simple task - should use base budget
        simple_budget = assembler._calculate_dynamic_budget("List files", memory)
        base_budget = config.curation_config.max_tokens
        assert simple_budget == base_budget, "Simple task should use base budget"

        # Test 2: Complex task - should increase budget
        complex_budget = assembler._calculate_dynamic_budget(
            "Analyze and refactor the authentication system",
            memory
        )
        assert complex_budget > base_budget, "Complex task should increase budget"

        # Test 3: With rich L4 context - should reduce budget
        for i in range(15):
            await memory.add(MemoryUnit(
                content=f"Fact {i}",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=0.9
            ))

        reduced_budget = assembler._calculate_dynamic_budget("Simple task", memory)
        assert reduced_budget < base_budget, "Rich L4 context should reduce budget"

        print("✅ Adaptive token budgeting: PASSED")
        print(f"   Base: {base_budget}, Complex: {complex_budget}, Reduced: {reduced_budget}")
        return True
    except Exception as e:
        print(f"❌ Adaptive token budgeting: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     PRIORITY 2 OPTIMIZATIONS - TEST SUITE               ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    tests = [
        test_tool_result_caching,
        test_cache_ttl_expiration,
        test_adaptive_token_budgeting
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
