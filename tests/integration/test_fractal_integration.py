"""
End-to-end integration tests for Fractal Architecture

Tests cover:
- Parent-child agent delegation
- Smart memory allocation
- Bidirectional memory flow
- Task execution with fractal memory
"""

import pytest

from loom.fractal.memory import FractalMemory, MemoryScope
from loom.orchestration.agent import Agent
from loom.protocol import Task
from loom.providers.llm.mock import MockLLMProvider


class TestFractalIntegration:
    """Test fractal architecture integration with Agent"""

    @pytest.mark.asyncio
    async def test_agent_with_fractal_memory(self):
        """Test Agent can use FractalMemory"""
        # Create Agent with fractal memory
        llm_provider = MockLLMProvider()
        agent = Agent(
            node_id="test-agent",
            llm_provider=llm_provider,
            system_prompt="Test agent",
        )

        # Add fractal_memory attribute
        agent.fractal_memory = FractalMemory(
            node_id="test-agent",
            base_memory=agent.memory,
        )

        # Write to fractal memory
        await agent.fractal_memory.write("key1", "value1", MemoryScope.LOCAL)

        # Read from fractal memory
        entry = await agent.fractal_memory.read("key1")

        assert entry is not None
        assert entry.content == "value1"
        assert entry.scope == MemoryScope.LOCAL

    @pytest.mark.asyncio
    async def test_create_child_node_with_memory_allocation(self):
        """Test creating child node with smart memory allocation"""
        llm_provider = MockLLMProvider()
        parent_agent = Agent(
            node_id="parent-agent",
            llm_provider=llm_provider,
            system_prompt="Parent agent",
        )

        # Add fractal_memory to parent
        parent_agent.fractal_memory = FractalMemory(
            node_id="parent-agent",
            base_memory=parent_agent.memory,
        )

        # Write some memories to parent
        await parent_agent.fractal_memory.write(
            "mem1", "API authentication logic", MemoryScope.SHARED
        )
        await parent_agent.fractal_memory.write(
            "mem2", "Database connection pool", MemoryScope.SHARED
        )

        # Create child task
        child_task = Task(
            task_id="child-task-1",
            action="execute",
            parameters={"content": "Fix API authentication bug"},
        )

        # Create child node
        child_agent = await parent_agent._create_child_node(
            subtask=child_task,
            context_hints=["mem1"],
        )

        # Verify child has fractal_memory
        assert hasattr(child_agent, "fractal_memory")
        assert child_agent.fractal_memory is not None

        # Verify child has inherited memories
        inherited = await child_agent.fractal_memory.list_by_scope(MemoryScope.INHERITED)
        assert len(inherited) > 0

    @pytest.mark.asyncio
    async def test_sync_memory_from_child(self):
        """Test bidirectional memory flow from child to parent"""
        llm_provider = MockLLMProvider()
        parent_agent = Agent(
            node_id="parent-agent",
            llm_provider=llm_provider,
            system_prompt="Parent agent",
        )

        # Add fractal_memory to parent
        parent_agent.fractal_memory = FractalMemory(
            node_id="parent-agent",
            base_memory=parent_agent.memory,
        )

        # Create child agent
        child_agent = Agent(
            node_id="child-agent",
            llm_provider=llm_provider,
            system_prompt="Child agent",
        )

        # Add fractal_memory to child with parent reference
        child_agent.fractal_memory = FractalMemory(
            node_id="child-agent",
            parent_memory=parent_agent.fractal_memory,
            base_memory=child_agent.memory,
        )

        # Child writes to SHARED scope
        await child_agent.fractal_memory.write(
            "child_result", "Task completed successfully", MemoryScope.SHARED
        )

        # Sync memory from child to parent
        await parent_agent._sync_memory_from_child(child_agent)

        # Verify parent received the memory
        parent_shared = await parent_agent.fractal_memory.list_by_scope(MemoryScope.SHARED)
        assert any(e.id == "child_result" for e in parent_shared)
