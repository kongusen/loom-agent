"""
End-to-end integration tests for Fractal Architecture

Tests cover:
- Parent-child agent delegation
- Smart memory allocation (MemoryManager)
- Bidirectional memory flow
- Task execution with unified memory
"""

import pytest

from loom.agent import Agent
from loom.fractal.memory import MemoryScope
from loom.protocol import Task
from loom.providers.llm.mock import MockLLMProvider


class TestFractalIntegration:
    """Test fractal architecture integration with Agent (single memory: MemoryManager)"""

    @pytest.mark.asyncio
    async def test_agent_with_fractal_memory(self):
        """Test Agent uses MemoryManager for scope-based memory"""
        llm_provider = MockLLMProvider()
        agent = Agent(
            node_id="test-agent",
            llm_provider=llm_provider,
            system_prompt="Test agent",
        )

        await agent.memory.write("key1", "value1", scope=MemoryScope.LOCAL)
        entry = await agent.memory.read("key1")

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

        await parent_agent.memory.write(
            "mem1", "API authentication logic", scope=MemoryScope.SHARED
        )
        await parent_agent.memory.write(
            "mem2", "Database connection pool", scope=MemoryScope.SHARED
        )

        child_task = Task(
            task_id="child-task-1",
            action="execute",
            parameters={"content": "Fix API authentication bug"},
        )

        child_agent = await parent_agent._create_child_node(
            subtask=child_task,
            context_hints=["mem1"],
        )

        assert child_agent.memory is not None
        assert child_agent.memory.parent is parent_agent.memory

        inherited = await child_agent.memory.list_by_scope(MemoryScope.INHERITED)
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

        child_task = Task(
            task_id="child-task-sync",
            action="execute",
            parameters={"content": "Child task"},
        )
        child_agent = await parent_agent._create_child_node(
            subtask=child_task,
            context_hints=[],
        )

        await child_agent.memory.write(
            "child_result", "Task completed successfully", scope=MemoryScope.SHARED
        )

        await parent_agent._sync_memory_from_child(child_agent)

        parent_shared = await parent_agent.memory.list_by_scope(MemoryScope.SHARED)
        assert any(e.id == "child_result" for e in parent_shared)
