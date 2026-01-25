"""
Memory Layer Integration Tests

Tests for layer coordination and promotion mechanisms.
"""

import pytest

from loom.memory.core import LoomMemory
from loom.memory.types import MemoryTier
from loom.protocol import Task


class TestLayerIntegration:
    """Integration tests for memory layer coordination"""

    @pytest.fixture
    def memory(self) -> LoomMemory:
        """Create a LoomMemory instance for testing"""
        return LoomMemory(
            node_id="test-node",
            max_l1_size=10,
            max_l2_size=5,
            max_l3_size=10,
            enable_l4_vectorization=False,
        )

    def test_l1_to_l2_promotion(self, memory: LoomMemory) -> None:
        """Test that important tasks are promoted from L1 to L2"""
        # Add tasks with varying importance to L1
        for i in range(5):
            task = Task(task_id=f"task-{i}", action="test_action")
            task.metadata["importance"] = 0.7 if i < 2 else 0.3  # First 2 are important
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # Trigger promotion
        memory.promote_tasks()

        # Check that important tasks were promoted to L2
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) >= 2, "Important tasks should be promoted to L2"

    def test_l2_to_l3_compression(self, memory: LoomMemory) -> None:
        """Test that L2 tasks are compressed to L3 summaries when L2 is full"""
        # Fill L2 with tasks (max_l2_size=5)
        for i in range(6):
            task = Task(task_id=f"task-{i}", action="test_action")
            task.metadata["importance"] = 0.5 + (i / 10.0)
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        # Trigger promotion (should compress L2 to L3)
        memory.promote_tasks()

        # Check that L3 has summaries
        l3_summaries = memory.get_l3_summaries()
        assert len(l3_summaries) > 0, "L2 tasks should be compressed to L3 summaries"
