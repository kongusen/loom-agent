"""
Index Context Tools Unit Tests

测试基于索引的上下文工具功能
"""

import pytest

from loom.memory.core import LoomMemory
from loom.memory.types import MemoryTier
from loom.protocol import Task, TaskStatus
from loom.tools.index_context_tools import (
    create_list_l2_memory_tool,
    create_list_l3_memory_tool,
    create_select_memory_by_index_tool,
    execute_list_l2_memory_tool,
    execute_list_l3_memory_tool,
    execute_select_memory_by_index_tool,
)


class TestCreateTools:
    """测试工具创建函数"""

    def test_create_list_l2_memory_tool(self):
        """测试创建 L2 记忆列表工具"""
        tool = create_list_l2_memory_tool()

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "list_l2_memory"
        assert "limit" in tool["function"]["parameters"]["properties"]

    def test_create_list_l3_memory_tool(self):
        """测试创建 L3 记忆列表工具"""
        tool = create_list_l3_memory_tool()

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "list_l3_memory"
        assert "limit" in tool["function"]["parameters"]["properties"]

    def test_create_select_memory_by_index_tool(self):
        """测试创建选择记忆工具"""
        tool = create_select_memory_by_index_tool()

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "select_memory_by_index"
        assert "layer" in tool["function"]["parameters"]["properties"]
        assert "indices" in tool["function"]["parameters"]["properties"]


class TestExecuteListL2MemoryTool:
    """测试执行 L2 记忆列表工具"""

    @pytest.mark.asyncio
    async def test_execute_list_l2_memory_tool(self):
        """测试执行 L2 记忆列表工具"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些任务到 L2
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"param1": f"value{i}"},
            )
            task.status = TaskStatus.COMPLETED
            task.metadata = {"importance": 0.8}
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await execute_list_l2_memory_tool({"limit": 10}, memory)

        assert result["layer"] == "L2"
        assert result["count"] > 0
        assert "items" in result
        assert len(result["items"]) > 0
        assert "index" in result["items"][0]
        assert "task_id" in result["items"][0]
        assert "preview" in result["items"][0]

    @pytest.mark.asyncio
    async def test_execute_list_l2_memory_tool_with_limit(self):
        """测试带限制的 L2 记忆列表"""
        memory = LoomMemory(node_id="test-node")

        # 添加多个任务
        for i in range(10):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"param1": f"value{i}"},
            )
            task.status = TaskStatus.COMPLETED
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await execute_list_l2_memory_tool({"limit": 5}, memory)

        assert result["count"] <= 5

    @pytest.mark.asyncio
    async def test_execute_list_l2_memory_tool_empty(self):
        """测试空记忆的 L2 列表"""
        memory = LoomMemory(node_id="test-node")

        result = await execute_list_l2_memory_tool({"limit": 10}, memory)

        assert result["count"] == 0
        assert result["items"] == []


class TestExecuteListL3MemoryTool:
    """测试执行 L3 记忆列表工具"""

    @pytest.mark.asyncio
    async def test_execute_list_l3_memory_tool(self):
        """测试执行 L3 记忆列表工具"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些任务（会自动生成摘要）
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"param1": f"value{i}"},
            )
            task.status = TaskStatus.COMPLETED
            memory.add_task(task)

        result = await execute_list_l3_memory_tool({"limit": 10}, memory)

        assert result["layer"] == "L3"
        assert "items" in result
        assert isinstance(result["count"], int)

    @pytest.mark.asyncio
    async def test_execute_list_l3_memory_tool_with_tags(self):
        """测试带标签的 L3 记忆列表"""
        memory = LoomMemory(node_id="test-node")

        # 添加带标签的任务
        task = Task(
            task_id="task-1",
            action="test_action",
            parameters={"param1": "value1"},
        )
        task.status = TaskStatus.COMPLETED
        memory.add_task(task)

        result = await execute_list_l3_memory_tool({"limit": 10}, memory)

        # 检查是否有标签字段
        if result["items"]:
            assert "tags" in result["items"][0]

    @pytest.mark.asyncio
    async def test_execute_list_l3_memory_tool_with_content(self):
        """测试L3列表包含内容预览（触发lines 150-152）"""
        memory = LoomMemory(node_id="test-node")

        # 添加任务并确保生成L3摘要
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action=f"action_{i}",
                parameters={"param1": f"value{i}"},
            )
            task.status = TaskStatus.COMPLETED
            task.result = {"output": f"result_{i}"}
            memory.add_task(task)

        result = await execute_list_l3_memory_tool({"limit": 10}, memory)

        # 验证包含预览和标签字段
        assert result["layer"] == "L3"
        if result["items"]:
            # 验证每个item都有preview字段（来自line 150）
            for item in result["items"]:
                assert "preview" in item
                assert "task_id" in item
                assert "index" in item
                assert "tags" in item


class TestExecuteSelectMemoryByIndexTool:
    """测试执行选择记忆工具"""

    @pytest.mark.asyncio
    async def test_execute_select_memory_by_index_l2(self):
        """测试选择 L2 记忆"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些任务
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"param1": f"value{i}"},
            )
            task.status = TaskStatus.COMPLETED
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await execute_select_memory_by_index_tool(
            {"layer": "L2", "indices": [1, 3]}, memory
        )

        assert result["layer"] == "L2"
        assert "selected" in result
        assert len(result["selected"]) == 2
        assert result["selected"][0]["index"] == 1
        assert result["selected"][1]["index"] == 3

    @pytest.mark.asyncio
    async def test_execute_select_memory_by_index_l3(self):
        """测试选择 L3 记忆"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些任务（会自动生成摘要）
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"param1": f"value{i}"},
            )
            task.status = TaskStatus.COMPLETED
            memory.add_task(task)

        result = await execute_select_memory_by_index_tool(
            {"layer": "L3", "indices": [1, 2]}, memory
        )

        assert result["layer"] == "L3"
        assert "selected" in result
        assert isinstance(result["selected"], list)

    @pytest.mark.asyncio
    async def test_execute_select_memory_by_index_l3_with_result_summary(self):
        """测试选择L3记忆包含结果摘要（触发lines 269-279）"""
        memory = LoomMemory(node_id="test-node")

        # 添加任务并设置结果，确保生成带result_summary的L3摘要
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action=f"action_{i}",
                parameters={"param1": f"value{i}"},
            )
            task.status = TaskStatus.COMPLETED
            task.result = f"This is a long result string for task {i} that should be summarized"
            memory.add_task(task)

        result = await execute_select_memory_by_index_tool(
            {"layer": "L3", "indices": [1, 2]}, memory
        )

        assert result["layer"] == "L3"
        if result["selected"]:
            # 验证L3的statement格式（来自lines 271-277）
            for item in result["selected"]:
                assert "index" in item
                assert "task_id" in item
                assert "statement" in item
                # L3 statement格式: "action: result_summary"
                assert ":" in item["statement"]

    @pytest.mark.asyncio
    async def test_execute_select_memory_by_index_no_indices(self):
        """测试没有提供索引"""
        memory = LoomMemory(node_id="test-node")

        result = await execute_select_memory_by_index_tool({"layer": "L2", "indices": []}, memory)

        assert "error" in result
        assert result["selected"] == []

    @pytest.mark.asyncio
    async def test_execute_select_memory_by_index_invalid_layer(self):
        """测试无效层级"""
        memory = LoomMemory(node_id="test-node")

        result = await execute_select_memory_by_index_tool({"layer": "L4", "indices": [1]}, memory)

        assert "error" in result
        assert "Invalid layer" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_select_memory_by_index_out_of_range(self):
        """测试索引超出范围"""
        memory = LoomMemory(node_id="test-node")

        # 只添加2个任务
        for i in range(2):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"param1": f"value{i}"},
            )
            task.status = TaskStatus.COMPLETED
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await execute_select_memory_by_index_tool(
            {"layer": "L2", "indices": [1, 5, 10]}, memory
        )

        # 应该只返回有效的索引
        assert len(result["selected"]) <= 2

    @pytest.mark.asyncio
    async def test_execute_select_memory_by_index_single_index(self):
        """测试选择单个索引"""
        memory = LoomMemory(node_id="test-node")

        task = Task(
            task_id="task-1",
            action="test_action",
            parameters={"param1": "value1"},
        )
        task.status = TaskStatus.COMPLETED
        memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await execute_select_memory_by_index_tool({"layer": "L2", "indices": [1]}, memory)

        assert len(result["selected"]) == 1
        assert result["selected"][0]["index"] == 1
        assert "task_id" in result["selected"][0]


class TestCreateAllIndexContextTools:
    """测试创建所有索引上下文工具"""

    def test_create_all_index_context_tools(self):
        """测试创建所有索引上下文工具"""
        from loom.tools.index_context_tools import create_all_index_context_tools

        tools = create_all_index_context_tools()

        assert isinstance(tools, list)
        assert len(tools) == 3

        tool_names = [tool["function"]["name"] for tool in tools]
        assert "list_l2_memory" in tool_names
        assert "list_l3_memory" in tool_names
        assert "select_memory_by_index" in tool_names


class TestIndexContextToolExecutor:
    """测试索引上下文工具执行器"""

    @pytest.mark.asyncio
    async def test_executor_init(self):
        """测试执行器初始化"""
        from loom.tools.index_context_tools import IndexContextToolExecutor

        memory = LoomMemory(node_id="test-node")
        executor = IndexContextToolExecutor(memory)

        assert executor.memory == memory
        assert hasattr(executor, "_executors")
        assert len(executor._executors) == 3

    @pytest.mark.asyncio
    async def test_executor_execute_list_l2(self):
        """测试执行器执行 list_l2_memory"""
        from loom.tools.index_context_tools import IndexContextToolExecutor

        memory = LoomMemory(node_id="test-node")
        executor = IndexContextToolExecutor(memory)

        # 添加测试数据
        task = Task(
            task_id="task-1",
            action="test_action",
            parameters={"param1": "value1"},
        )
        task.status = TaskStatus.COMPLETED
        memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await executor.execute("list_l2_memory", {"limit": 10})

        assert result["layer"] == "L2"
        assert "items" in result

    @pytest.mark.asyncio
    async def test_executor_execute_list_l3(self):
        """测试执行器执行 list_l3_memory"""
        from loom.tools.index_context_tools import IndexContextToolExecutor

        memory = LoomMemory(node_id="test-node")
        executor = IndexContextToolExecutor(memory)

        # 添加测试数据
        task = Task(
            task_id="task-1",
            action="test_action",
            parameters={"param1": "value1"},
        )
        task.status = TaskStatus.COMPLETED
        memory.add_task(task)

        result = await executor.execute("list_l3_memory", {"limit": 10})

        assert result["layer"] == "L3"
        assert "items" in result

    @pytest.mark.asyncio
    async def test_executor_execute_select_memory(self):
        """测试执行器执行 select_memory_by_index"""
        from loom.tools.index_context_tools import IndexContextToolExecutor

        memory = LoomMemory(node_id="test-node")
        executor = IndexContextToolExecutor(memory)

        # 添加测试数据
        task = Task(
            task_id="task-1",
            action="test_action",
            parameters={"param1": "value1"},
        )
        task.status = TaskStatus.COMPLETED
        memory.add_task(task, tier=MemoryTier.L2_WORKING)

        result = await executor.execute("select_memory_by_index", {"layer": "L2", "indices": [1]})

        assert result["layer"] == "L2"
        assert "selected" in result

    @pytest.mark.asyncio
    async def test_executor_execute_unknown_tool(self):
        """测试执行器执行未知工具"""
        from loom.tools.index_context_tools import IndexContextToolExecutor

        memory = LoomMemory(node_id="test-node")
        executor = IndexContextToolExecutor(memory)

        with pytest.raises(ValueError, match="Unknown index context tool"):
            await executor.execute("unknown_tool", {})
