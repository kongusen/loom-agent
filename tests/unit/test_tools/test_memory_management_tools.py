"""
Tests for Memory Management Tools
"""


import pytest

from loom.memory.core import LoomMemory
from loom.protocol.task import Task
from loom.tools.memory_management_tools import (
    MemoryManagementToolExecutor,
    create_all_memory_management_tools,
    create_create_task_summary_tool,
    create_get_memory_stats_tool,
    create_promote_task_to_l2_tool,
    execute_create_task_summary_tool,
    execute_get_memory_stats_tool,
    execute_promote_task_to_l2_tool,
)


class TestMemoryStatsTool:
    """Test suite for get_memory_stats tool"""

    def test_create_get_memory_stats_tool(self):
        """Test creating the memory stats tool definition"""
        tool_def = create_get_memory_stats_tool()

        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "get_memory_stats"
        assert "parameters" in tool_def["function"]
        assert tool_def["function"]["parameters"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_execute_get_memory_stats_tool(self):
        """Test executing get memory stats"""
        memory = LoomMemory(
            node_id="test_node",
            max_l1_size=50,
            max_l2_size=100,
            max_l3_size=500,
            enable_l4_vectorization=True,
        )

        # Add some test data
        task1 = Task(
            task_id="task1",
            action="test_action",
            parameters={"key": "value"},
        )
        memory.add_task(task1)

        result = await execute_get_memory_stats_tool({}, memory)

        assert "l1" in result
        assert "l2" in result
        assert "l3" in result
        assert "l4" in result
        assert result["l1"]["max"] == 50
        assert result["l2"]["max"] == 100
        assert result["l3"]["max"] == 500
        assert result["l4"]["enabled"] is True
        assert result["task_index_size"] >= 0
        assert result["fact_index_size"] >= 0

    @pytest.mark.asyncio
    async def test_execute_get_memory_stats_with_l4_disabled(self):
        """Test get memory stats with L4 disabled"""
        memory = LoomMemory(
            node_id="test_node",
            enable_l4_vectorization=False,
        )

        result = await execute_get_memory_stats_tool({}, memory)

        assert result["l4"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_execute_get_memory_stats_empty_memory(self):
        """Test get memory stats on empty memory"""
        memory = LoomMemory(node_id="test_node")

        result = await execute_get_memory_stats_tool({}, memory)

        assert result["l1"]["current"] == 0
        assert result["l2"]["current"] == 0
        assert result["l3"]["current"] == 0

    @pytest.mark.asyncio
    async def test_execute_get_memory_stats_usage_percent(self):
        """Test usage percentage calculation"""
        memory = LoomMemory(
            node_id="test_node",
            max_l1_size=100,
            max_l2_size=200,
            max_l3_size=500,
        )

        # Add tasks to L1
        for i in range(50):
            task = Task(
                task_id=f"task_{i}",
                action="test_action",
                parameters={"index": i},
            )
            memory.add_task(task)

        result = await execute_get_memory_stats_tool({}, memory)

        assert result["l1"]["usage_percent"] == 50.0


class TestPromoteTaskToL2Tool:
    """Test suite for promote_task_to_l2 tool"""

    def test_create_promote_task_to_l2_tool(self):
        """Test creating the promote task to L2 tool definition"""
        tool_def = create_promote_task_to_l2_tool()

        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "promote_task_to_l2"
        params = tool_def["function"]["parameters"]
        assert params["type"] == "object"
        assert "task_id" in params["properties"]
        assert "reason" in params["properties"]
        assert "task_id" in params["required"]

    @pytest.mark.asyncio
    async def test_execute_promote_task_to_l2_success(self):
        """Test successfully promoting a task to L2"""
        memory = LoomMemory(node_id="test_node")

        # Add a task to L1
        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={"key": "value"},
            metadata={"importance": 0.8},
        )
        memory.add_task(task)

        result = await execute_promote_task_to_l2_tool(
            {"task_id": "test_task", "reason": "Important task"}, memory
        )

        assert result["success"] is True
        assert result["task_id"] == "test_task"
        assert result["l2_size"] == 1

    @pytest.mark.asyncio
    async def test_execute_promote_task_to_l2_not_found(self):
        """Test promoting a non-existent task"""
        memory = LoomMemory(node_id="test_node")

        result = await execute_promote_task_to_l2_tool(
            {"task_id": "nonexistent", "reason": "Test"}, memory
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_promote_task_to_l2_already_in_l2(self):
        """Test promoting a task that's already in L2"""
        memory = LoomMemory(node_id="test_node")

        # Add task to L1
        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={"key": "value"},
            metadata={"importance": 0.8},
        )
        memory.add_task(task)

        # Promote to L2
        await execute_promote_task_to_l2_tool(
            {"task_id": "test_task", "reason": "First promotion"}, memory
        )

        # Try to promote again
        result = await execute_promote_task_to_l2_tool(
            {"task_id": "test_task", "reason": "Second promotion"}, memory
        )

        assert result["success"] is False
        assert "already in L2" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_promote_task_to_l2_default_reason(self):
        """Test promoting with default reason"""
        memory = LoomMemory(node_id="test_node")

        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
        )
        memory.add_task(task)

        result = await execute_promote_task_to_l2_tool({"task_id": "test_task"}, memory)

        assert result["success"] is True
        assert result["reason"] == "LLM decision"

    @pytest.mark.asyncio
    async def test_execute_promote_task_to_l2_multiple_tasks(self):
        """Test promoting multiple tasks"""
        memory = LoomMemory(node_id="test_node")

        # Add multiple tasks
        for i in range(5):
            task = Task(
                task_id=f"task_{i}",
                action="test_action",
                parameters={"index": i},
            )
            memory.add_task(task)

        # Promote two of them
        result1 = await execute_promote_task_to_l2_tool(
            {"task_id": "task_1", "reason": "Important"}, memory
        )
        result2 = await execute_promote_task_to_l2_tool(
            {"task_id": "task_3", "reason": "Also important"}, memory
        )

        assert result1["success"] is True
        assert result2["success"] is True
        assert result1["l2_size"] == 1
        assert result2["l2_size"] == 2


class TestCreateTaskSummaryTool:
    """Test suite for create_task_summary tool"""

    def test_create_create_task_summary_tool(self):
        """Test creating the create task summary tool definition"""
        tool_def = create_create_task_summary_tool()

        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "create_task_summary"
        params = tool_def["function"]["parameters"]
        assert params["type"] == "object"
        assert "task_id" in params["properties"]
        assert "summary" in params["properties"]
        assert "importance" in params["properties"]
        assert "tags" in params["properties"]
        assert "task_id" in params["required"]
        assert "summary" in params["required"]

    @pytest.mark.asyncio
    async def test_execute_create_task_summary_success(self):
        """Test successfully creating a task summary"""
        memory = LoomMemory(node_id="test_node")

        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={"input": "value"},
        )
        memory.add_task(task)

        result = await execute_create_task_summary_tool(
            {
                "task_id": "test_task",
                "summary": "Task completed successfully",
                "importance": 0.8,
                "tags": ["test", "success"],
            },
            memory,
        )

        assert result["success"] is True
        assert result["task_id"] == "test_task"
        assert result["summary"] == "Task completed successfully"
        assert result["l3_size"] == 1

    @pytest.mark.asyncio
    async def test_execute_create_task_summary_not_found(self):
        """Test creating summary for non-existent task"""
        memory = LoomMemory(node_id="test_node")

        result = await execute_create_task_summary_tool(
            {
                "task_id": "nonexistent",
                "summary": "Test summary",
            },
            memory,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_create_task_summary_minimal_args(self):
        """Test creating summary with minimal arguments"""
        memory = LoomMemory(node_id="test_node")

        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
        )
        memory.add_task(task)

        result = await execute_create_task_summary_tool(
            {
                "task_id": "test_task",
                "summary": "Brief summary",
            },
            memory,
        )

        assert result["success"] is True
        assert result["l3_size"] == 1

    @pytest.mark.asyncio
    async def test_execute_create_task_summary_with_tags(self):
        """Test creating summary with custom tags"""
        memory = LoomMemory(node_id="test_node")

        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
        )
        memory.add_task(task)

        result = await execute_create_task_summary_tool(
            {
                "task_id": "test_task",
                "summary": "Summary with tags",
                "tags": ["important", "user-request"],
            },
            memory,
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_create_task_summary_check_l3_content(self):
        """Test that summary is actually stored in L3"""
        memory = LoomMemory(node_id="test_node")

        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={"input": "value"},
        )
        memory.add_task(task)

        await execute_create_task_summary_tool(
            {
                "task_id": "test_task",
                "summary": "Test summary",
                "importance": 0.7,
                "tags": ["test"],
            },
            memory,
        )

        l3_summaries = memory.get_l3_summaries()
        assert len(l3_summaries) == 1
        assert l3_summaries[0].task_id == "test_task"
        assert l3_summaries[0].result_summary == "Test summary"
        assert l3_summaries[0].importance == 0.7
        assert l3_summaries[0].tags == ["test"]


class TestCreateAllMemoryManagementTools:
    """Test suite for create_all_memory_management_tools"""

    def test_create_all_memory_management_tools(self):
        """Test creating all memory management tools"""
        tools = create_all_memory_management_tools()

        assert len(tools) == 3
        tool_names = [t["function"]["name"] for t in tools]
        assert "get_memory_stats" in tool_names
        assert "promote_task_to_l2" in tool_names
        assert "create_task_summary" in tool_names


class TestMemoryManagementToolExecutor:
    """Test suite for MemoryManagementToolExecutor"""

    @pytest.fixture
    def memory(self):
        """Create a memory instance for testing"""
        return LoomMemory(node_id="test_node")

    @pytest.fixture
    def executor(self, memory):
        """Create an executor instance"""
        return MemoryManagementToolExecutor(memory)

    def test_init(self, executor, memory):
        """Test executor initialization"""
        assert executor.memory is memory
        assert "get_memory_stats" in executor._executors
        assert "promote_task_to_l2" in executor._executors
        assert "create_task_summary" in executor._executors

    @pytest.mark.asyncio
    async def test_execute_get_memory_stats(self, executor):
        """Test executing get_memory_stats through executor"""
        result = await executor.execute("get_memory_stats", {})

        assert "l1" in result
        assert "l2" in result
        assert "l3" in result

    @pytest.mark.asyncio
    async def test_execute_promote_task_to_l2(self, executor, memory):
        """Test executing promote_task_to_l2 through executor"""
        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
        )
        memory.add_task(task)

        result = await executor.execute("promote_task_to_l2", {"task_id": "test_task"})

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_create_task_summary(self, executor, memory):
        """Test executing create_task_summary through executor"""
        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
        )
        memory.add_task(task)

        result = await executor.execute(
            "create_task_summary",
            {"task_id": "test_task", "summary": "Test summary"},
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, executor):
        """Test executing an unknown tool"""
        with pytest.raises(ValueError, match="Unknown memory management tool"):
            await executor.execute("unknown_tool", {})

    @pytest.mark.asyncio
    async def test_execute_passes_args_correctly(self, executor, memory):
        """Test that arguments are passed correctly"""
        task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
        )
        memory.add_task(task)

        result = await executor.execute(
            "promote_task_to_l2",
            {"task_id": "test_task", "reason": "Custom reason"},
        )

        assert result["success"] is True
