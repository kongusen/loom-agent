"""
Phase 2 Performance Testing

Tests performance metrics mentioned in the implementation plan:
1. Agent response time (should be < 2 seconds)
2. Memory usage (should not continuously grow)
3. Context building performance
4. Parent-child memory operations
"""

import asyncio
import time
import tracemalloc

import pytest

from loom.agent.core import Agent
from loom.fractal.memory import MemoryScope
from loom.memory.manager import MemoryManager
from loom.memory.orchestrator import ContextOrchestrator
from loom.memory.task_context import MemoryContextSource
from loom.memory.tokenizer import EstimateCounter
from loom.protocol import Task, TaskStatus


class MockLLMProvider:
    """Mock LLM provider for testing"""

    async def generate(self, messages, tools=None, **kwargs):
        """Mock generate that returns a done tool call"""
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "done", "arguments": '{"result": "Test completed"}'},
                }
            ],
        }


@pytest.mark.asyncio
async def test_agent_response_time():
    """Test that Agent response time is < 2 seconds"""
    # Create Agent with mock LLM
    agent = Agent(
        node_id="perf-test",
        llm_provider=MockLLMProvider(),
        system_prompt="Test agent",
        require_done_tool=True,
    )

    # Measure execution time
    task = Task(
        task_id="test-1",
        action="execute",
        parameters={"content": "Simple test task"},
        session_id="session-1",
    )

    start_time = time.time()
    result = await agent.execute_task(task)
    duration = time.time() - start_time

    # Verify response time
    assert duration < 2.0, f"Agent response time {duration:.2f}s exceeds 2s threshold"
    assert result.status == TaskStatus.COMPLETED
    print(f"✓ Agent response time: {duration:.3f}s (< 2s threshold)")


@pytest.mark.asyncio
async def test_memory_usage_stability():
    """Test that memory usage doesn't continuously grow"""
    tracemalloc.start()

    # Create memory manager
    memory = MemoryManager(node_id="mem-test")

    # Baseline memory
    baseline_snapshot = tracemalloc.take_snapshot()

    # Perform 100 write/read operations
    for i in range(100):
        await memory.write(f"key_{i}", f"value_{i}", MemoryScope.LOCAL)
        await memory.read(f"key_{i}")

    # Check memory after operations
    current_snapshot = tracemalloc.take_snapshot()
    top_stats = current_snapshot.compare_to(baseline_snapshot, "lineno")

    # Calculate total memory increase
    total_increase = sum(stat.size_diff for stat in top_stats)

    tracemalloc.stop()

    # Memory increase should be reasonable (< 1MB for 100 operations)
    assert (
        total_increase < 1024 * 1024
    ), f"Memory increased by {total_increase / 1024:.1f}KB (> 1MB threshold)"
    print(f"✓ Memory usage stable: {total_increase / 1024:.1f}KB increase for 100 operations")


@pytest.mark.asyncio
async def test_context_building_performance():
    """Test that context building is fast"""
    # Create memory with some tasks
    memory = MemoryManager(node_id="ctx-test")

    # Add 50 tasks to memory
    for i in range(50):
        task = Task(
            task_id=f"task_{i}",
            action="execute",
            parameters={"content": f"Task {i} content"},
            session_id="session-1",
        )
        memory.add_task(task)

    # Create context orchestrator
    counter = EstimateCounter()
    source = MemoryContextSource(memory._loom_memory)
    orchestrator = ContextOrchestrator(
        token_counter=counter, sources=[source], max_tokens=4000, system_prompt="Test system"
    )

    # Measure context building time
    current_task = Task(
        task_id="current",
        action="execute",
        parameters={"content": "Current task"},
        session_id="session-1",
    )

    start_time = time.time()
    messages = await orchestrator.build_context(current_task)
    duration = time.time() - start_time

    # Context building should be fast (< 0.1s)
    assert duration < 0.1, f"Context building took {duration:.3f}s (> 0.1s threshold)"
    assert len(messages) > 0
    print(f"✓ Context building: {duration:.3f}s for 50 tasks (< 0.1s threshold)")


@pytest.mark.asyncio
async def test_parent_child_memory_performance():
    """Test parent-child memory operations performance"""
    # Create parent and child
    parent = MemoryManager(node_id="parent")
    child = MemoryManager(node_id="child", parent=parent)

    # Parent writes to SHARED scope
    start_time = time.time()
    for i in range(20):
        await parent.write(f"shared_{i}", f"value_{i}", MemoryScope.SHARED)
    write_duration = time.time() - start_time

    # Child reads from INHERITED scope
    start_time = time.time()
    for i in range(20):
        entry = await child.read(f"shared_{i}", [MemoryScope.INHERITED])
        assert entry is not None
    read_duration = time.time() - start_time

    # Operations should be fast
    assert write_duration < 0.1, f"Parent writes took {write_duration:.3f}s (> 0.1s threshold)"
    assert read_duration < 0.1, f"Child reads took {read_duration:.3f}s (> 0.1s threshold)"
    print(
        f"✓ Parent-child memory: write={write_duration:.3f}s, read={read_duration:.3f}s (< 0.1s each)"
    )


@pytest.mark.asyncio
async def test_concurrent_memory_operations():
    """Test concurrent memory operations don't cause issues"""
    memory = MemoryManager(node_id="concurrent-test")

    async def write_task(task_id: int):
        """Write task"""
        await memory.write(f"key_{task_id}", f"value_{task_id}", MemoryScope.LOCAL)

    async def read_task(task_id: int):
        """Read task"""
        await memory.read(f"key_{task_id}")

    # Run 10 concurrent writes
    start_time = time.time()
    await asyncio.gather(*[write_task(i) for i in range(10)])
    write_duration = time.time() - start_time

    # Run 10 concurrent reads
    start_time = time.time()
    await asyncio.gather(*[read_task(i) for i in range(10)])
    read_duration = time.time() - start_time

    # Concurrent operations should complete quickly
    assert write_duration < 0.5, f"Concurrent writes took {write_duration:.3f}s (> 0.5s threshold)"
    assert read_duration < 0.5, f"Concurrent reads took {read_duration:.3f}s (> 0.5s threshold)"
    print(
        f"✓ Concurrent operations: write={write_duration:.3f}s, read={read_duration:.3f}s (< 0.5s each)"
    )


if __name__ == "__main__":
    # Run tests manually
    asyncio.run(test_agent_response_time())
    asyncio.run(test_memory_usage_stability())
    asyncio.run(test_context_building_performance())
    asyncio.run(test_parent_child_memory_performance())
    asyncio.run(test_concurrent_memory_operations())
    print("\n✅ All Phase 2 performance tests passed!")
