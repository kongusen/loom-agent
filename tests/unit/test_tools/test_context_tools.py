"""
Context Tools Unit Tests

测试上下文查询工具功能
"""

import pytest

from loom.memory.core import LoomMemory
from loom.memory.types import MemoryTier, TaskSummary
from loom.protocol import Task, TaskStatus
from loom.tools.context_tools import (
    ContextToolExecutor,
    create_all_context_tools,
    create_query_l1_memory_tool,
    create_query_l2_memory_tool,
    create_query_l3_memory_tool,
    create_query_l4_memory_tool,
    execute_query_l1_memory_tool,
    execute_query_l2_memory_tool,
    execute_query_l3_memory_tool,
    execute_query_l4_memory_tool,
)


class TestCreateMemoryQueryTools:
    """测试创建记忆查询工具"""

    def test_create_query_l1_memory_tool(self):
        """测试创建 L1 记忆查询工具"""
        tool = create_query_l1_memory_tool()

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "query_l1_memory"
        assert "limit" in tool["function"]["parameters"]["properties"]

    def test_create_query_l2_memory_tool(self):
        """测试创建 L2 记忆查询工具"""
        tool = create_query_l2_memory_tool()

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "query_l2_memory"
        assert "limit" in tool["function"]["parameters"]["properties"]

    def test_create_query_l3_memory_tool(self):
        """测试创建 L3 记忆查询工具"""
        tool = create_query_l3_memory_tool()

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "query_l3_memory"
        assert "limit" in tool["function"]["parameters"]["properties"]

    def test_create_query_l4_memory_tool(self):
        """测试创建 L4 记忆查询工具"""
        tool = create_query_l4_memory_tool()

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "query_l4_memory"
        assert "query" in tool["function"]["parameters"]["properties"]
        assert "limit" in tool["function"]["parameters"]["properties"]


class TestExecuteQueryL1MemoryTool:
    """测试执行 L1 记忆查询工具"""

    @pytest.mark.asyncio
    async def test_execute_query_l1_memory_tool(self):
        """测试执行 L1 记忆查询"""
        memory = LoomMemory(node_id="test-node")

        # 添加任务到 L1
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"index": i},
            )
            task.status = TaskStatus.COMPLETED
            task.result = f"result{i}"
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        result = await execute_query_l1_memory_tool({"limit": 10}, memory)

        assert result["layer"] == "L1"
        assert result["count"] == 3
        assert "tasks" in result
        assert len(result["tasks"]) == 3
        assert result["tasks"][0]["task_id"] == "task-0"

    @pytest.mark.asyncio
    async def test_execute_query_l1_memory_tool_with_limit(self):
        """测试带限制的 L1 记忆查询"""
        memory = LoomMemory(node_id="test-node")

        # 添加多个任务
        for i in range(10):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
            )
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        result = await execute_query_l1_memory_tool({"limit": 5}, memory)

        assert result["count"] <= 5


class TestExecuteQueryL2MemoryTool:
    """测试执行 L2 记忆查询工具"""

    @pytest.mark.asyncio
    async def test_execute_query_l2_memory_tool(self):
        """测试执行 L2 记忆查询"""
        memory = LoomMemory(node_id="test-node")

        # 添加任务到 L2
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"key": f"value{i}"},
            )
            task.metadata["importance"] = 0.8
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await execute_query_l2_memory_tool({"limit": 10}, memory)

        assert result["layer"] == "L2"
        assert result["count"] == 3
        assert "statements" in result
        assert len(result["statements"]) == 3
        assert "statement" in result["statements"][0]

    @pytest.mark.asyncio
    async def test_execute_query_l2_memory_tool_long_content(self):
        """测试长内容的 L2 记忆查询"""
        memory = LoomMemory(node_id="test-node")

        # 添加带长参数和结果的任务
        task = Task(
            task_id="task-1",
            action="file_read",
            parameters={"file": "a" * 100},  # 长参数
        )
        task.result = "x" * 200  # 长结果
        task.metadata["importance"] = 0.8
        memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await execute_query_l2_memory_tool({"limit": 10}, memory)

        assert result["count"] == 1
        statement = result["statements"][0]["statement"]
        # 应该被截断
        assert len(statement) < 500


class TestExecuteQueryL3MemoryTool:
    """测试执行 L3 记忆查询工具"""

    @pytest.mark.asyncio
    async def test_execute_query_l3_memory_tool(self):
        """测试执行 L3 记忆查询"""
        memory = LoomMemory(node_id="test-node")

        # 添加摘要到 L3
        for i in range(3):
            summary = TaskSummary(
                task_id=f"task-{i}",
                action="test_action",
                param_summary=f"param{i}",
                result_summary=f"result{i}",
            )
            memory._add_to_l3(summary)

        result = await execute_query_l3_memory_tool({"limit": 10}, memory)

        assert result["layer"] == "L3"
        assert result["count"] == 3
        assert "statements" in result
        assert len(result["statements"]) == 3


class TestExecuteQueryL4MemoryTool:
    """测试执行 L4 记忆查询工具"""

    @pytest.mark.asyncio
    async def test_execute_query_l4_memory_tool(self):
        """测试执行 L4 记忆查询"""
        memory = LoomMemory(node_id="test-node")

        # 添加任务（会使用简单搜索）
        task = Task(
            task_id="task-1",
            action="test_action",
            parameters={"key": "test"},
        )
        memory.add_task(task)

        result = await execute_query_l4_memory_tool({"query": "test_action", "limit": 5}, memory)

        assert result["layer"] == "L4"
        assert "query" in result
        assert "statements" in result


class TestCreateAllContextTools:
    """测试创建所有上下文工具"""

    def test_create_all_context_tools(self):
        """测试创建所有上下文工具"""
        tools = create_all_context_tools()

        assert isinstance(tools, list)
        # Phase 3: Only Memory tools, not EventBus tools
        assert len(tools) == 4
        # 检查是否包含所有Memory工具
        tool_names = [t["function"]["name"] for t in tools]
        assert "query_l1_memory" in tool_names
        assert "query_l2_memory" in tool_names
        assert "query_l3_memory" in tool_names
        assert "query_l4_memory" in tool_names


class TestContextToolExecutor:
    """测试上下文工具执行器"""

    @pytest.fixture
    def executor(self):
        """提供执行器实例"""
        memory = LoomMemory(node_id="test-node")
        return ContextToolExecutor(memory)

    @pytest.mark.asyncio
    async def test_execute_query_l1_memory(self, executor):
        """测试执行 L1 记忆查询"""
        # 添加任务
        task = Task(task_id="task-1", action="test_action")
        executor.memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        result = await executor.execute("query_l1_memory", {"limit": 10})

        assert result["layer"] == "L1"
        assert result["count"] > 0

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, executor):
        """测试执行未知工具"""
        with pytest.raises(ValueError, match="Unknown context tool"):
            await executor.execute("unknown_tool", {})
