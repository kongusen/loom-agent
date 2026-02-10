"""
Memory Layer Contract Tests

Ensures all layer implementations conform to the MemoryLayer interface contract.
"""

import pytest

from loom.memory.layers import CircularBufferLayer, MemoryLayer, PriorityQueueLayer
from loom.runtime import Task


class TestLayerContract:
    """Test that all layers conform to the MemoryLayer interface"""

    @pytest.fixture
    def sample_tasks(self) -> list[Task]:
        """Create sample tasks for testing"""
        tasks = []
        for i in range(10):
            task = Task(task_id=f"task-{i}", action="test_action")
            task.metadata["importance"] = i / 10.0
            tasks.append(task)
        return tasks

    @pytest.mark.asyncio
    async def test_circular_buffer_layer_contract(self, sample_tasks: list[Task]) -> None:
        """Test CircularBufferLayer conforms to MemoryLayer interface"""
        layer: MemoryLayer[Task] = CircularBufferLayer(max_size=5)

        # Test add method
        for task in sample_tasks[:3]:
            await layer.add(task)

        # Test size method
        assert layer.size() == 3

        # Test retrieve method
        retrieved = await layer.retrieve(None, limit=2)
        assert len(retrieved) == 2

        # Test evict method
        evicted = await layer.evict(count=1)
        assert len(evicted) == 1
        assert layer.size() == 2

        # Test clear method
        layer.clear()
        assert layer.size() == 0

    @pytest.mark.asyncio
    async def test_priority_queue_layer_contract(self, sample_tasks: list[Task]) -> None:
        """Test PriorityQueueLayer conforms to MemoryLayer interface"""
        layer: MemoryLayer[Task] = PriorityQueueLayer(max_size=5)

        # Test add method
        for task in sample_tasks[:3]:
            await layer.add(task)

        # Test size method
        assert layer.size() == 3

        # Test retrieve method
        retrieved = await layer.retrieve(None, limit=2)
        assert len(retrieved) == 2

        # Test evict method
        evicted = await layer.evict(count=1)
        assert len(evicted) == 1
        assert layer.size() == 2

        # Test clear method
        layer.clear()
        assert layer.size() == 0
