"""
Memory Layer Performance Tests

Benchmarks for memory layer operations to ensure performance targets are met.
"""

import time

import pytest

from loom.memory.layers import CircularBufferLayer, PriorityQueueLayer
from loom.protocol import Task


class TestPerformance:
    """Performance benchmark tests for memory layers"""

    @pytest.mark.asyncio
    async def test_l1_insertion_performance(self) -> None:
        """Test L1 (CircularBuffer) insertion performance"""
        layer = CircularBufferLayer(max_size=100)

        # Create 1000 tasks
        tasks = []
        for i in range(1000):
            task = Task(task_id=f"task-{i}", action="test_action")
            task.metadata["importance"] = i / 1000.0
            tasks.append(task)

        # Measure insertion time
        start = time.perf_counter()
        for task in tasks:
            await layer.add(task)
        elapsed = time.perf_counter() - start

        # Target: < 10ms for 1000 insertions
        assert elapsed < 0.01, f"L1 insertion too slow: {elapsed:.4f}s (target: < 0.01s)"
        print(f"L1 insertion: {elapsed:.4f}s for 1000 tasks")

    @pytest.mark.asyncio
    async def test_l2_insertion_performance(self) -> None:
        """Test L2 (PriorityQueue) insertion performance - O(log n)"""
        layer = PriorityQueueLayer(max_size=100)

        # Create 1000 tasks
        tasks = []
        for i in range(1000):
            task = Task(task_id=f"task-{i}", action="test_action")
            task.metadata["importance"] = i / 1000.0
            tasks.append(task)

        # Measure insertion time
        start = time.perf_counter()
        for task in tasks:
            await layer.add(task)
        elapsed = time.perf_counter() - start

        # Target: < 50ms for 1000 insertions (100x improvement from O(n log n))
        assert elapsed < 0.05, f"L2 insertion too slow: {elapsed:.4f}s (target: < 0.05s)"
        print(f"L2 insertion: {elapsed:.4f}s for 1000 tasks")
