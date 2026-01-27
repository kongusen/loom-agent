"""
Memory Integration Tests

测试LoomMemory的核心功能：
1. L1-L4记忆层级管理
2. 任务存储和检索
3. 记忆统计信息
4. 记忆层级转换
"""

import pytest

from loom.memory.core import LoomMemory, MemoryTier
from loom.protocol import Task, TaskStatus


class TestL1Memory:
    """测试L1记忆（最近任务缓冲区）"""

    @pytest.mark.asyncio
    async def test_l1_stores_recent_tasks(self):
        """测试L1存储最近的任务"""
        # 1. 创建LoomMemory（L1最大容量为5）
        memory = LoomMemory(node_id="test-node", max_l1_size=5)

        # 2. 添加3个任务到L1
        tasks = []
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="execute",
                parameters={"content": f"Task {i}"},
                status=TaskStatus.COMPLETED,
                result={"content": f"Result {i}"},
            )
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)
            tasks.append(task)

        # 3. 验证L1包含这3个任务
        l1_tasks = memory.get_l1_tasks()
        assert len(l1_tasks) == 3, f"Expected 3 tasks in L1, got {len(l1_tasks)}"

        # 4. 验证任务内容正确
        for i, task in enumerate(l1_tasks):
            assert task.task_id == f"task-{i}"
            assert task.parameters["content"] == f"Task {i}"

        print(f"\n[SUCCESS] L1 memory stores {len(l1_tasks)} recent tasks correctly")

    @pytest.mark.asyncio
    async def test_l1_circular_buffer_behavior(self):
        """测试L1循环缓冲区行为（超出容量时覆盖旧任务）"""
        # 1. 创建LoomMemory（L1最大容量为3）
        memory = LoomMemory(node_id="test-node", max_l1_size=3)

        # 2. 添加5个任务（超出L1容量）
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="execute",
                parameters={"content": f"Task {i}"},
                status=TaskStatus.COMPLETED,
            )
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 3. 验证L1只保留最近的3个任务
        l1_tasks = memory.get_l1_tasks()
        assert len(l1_tasks) == 3, f"Expected 3 tasks in L1 (circular buffer), got {len(l1_tasks)}"

        # 4. 验证保留的是最新的任务（task-2, task-3, task-4）
        task_ids = [task.task_id for task in l1_tasks]
        assert "task-2" in task_ids, "Expected task-2 in L1"
        assert "task-3" in task_ids, "Expected task-3 in L1"
        assert "task-4" in task_ids, "Expected task-4 in L1"

        # 5. 验证旧任务被移除
        assert "task-0" not in task_ids, "Expected task-0 to be removed from L1"
        assert "task-1" not in task_ids, "Expected task-1 to be removed from L1"

        print(
            f"\n[SUCCESS] L1 circular buffer works correctly - keeps latest {len(l1_tasks)} tasks"
        )


class TestL2Memory:
    """测试L2记忆（工作记忆）"""

    @pytest.mark.asyncio
    async def test_l2_stores_important_tasks(self):
        """测试L2存储重要任务"""
        # 1. 创建LoomMemory
        memory = LoomMemory(node_id="test-node", max_l2_size=5)

        # 2. 添加3个任务到L2
        for i in range(3):
            task = Task(
                task_id=f"important-task-{i}",
                action="execute",
                parameters={"content": f"Important task {i}"},
                status=TaskStatus.COMPLETED,
                result={"content": f"Result {i}"},
            )
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        # 3. 验证L2包含这3个任务
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) == 3, f"Expected 3 tasks in L2, got {len(l2_tasks)}"

        # 4. 验证任务内容正确
        task_ids = [task.task_id for task in l2_tasks]
        for i in range(3):
            assert f"important-task-{i}" in task_ids

        print(f"\n[SUCCESS] L2 memory stores {len(l2_tasks)} important tasks correctly")

    @pytest.mark.asyncio
    async def test_l2_capacity_limit(self):
        """测试L2容量限制"""
        # 1. 创建LoomMemory（L2最大容量为3）
        memory = LoomMemory(node_id="test-node", max_l2_size=3)

        # 2. 添加5个任务到L2（超出容量）
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="execute",
                parameters={"content": f"Task {i}"},
                status=TaskStatus.COMPLETED,
            )
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        # 3. 验证L2只保留3个任务（容量限制）
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) <= 3, f"Expected at most 3 tasks in L2, got {len(l2_tasks)}"

        print(f"\n[SUCCESS] L2 capacity limit works - keeps {len(l2_tasks)} tasks (max 3)")


class TestMemoryStats:
    """测试记忆统计功能"""

    @pytest.mark.asyncio
    async def test_memory_stats_basic(self):
        """测试基础记忆统计信息"""
        # 1. 创建LoomMemory
        memory = LoomMemory(node_id="test-node", max_l1_size=5, max_l2_size=3)

        # 2. 添加任务到不同层级
        # 添加3个任务到L1
        for i in range(3):
            task = Task(
                task_id=f"l1-task-{i}",
                action="execute",
                parameters={"content": f"L1 Task {i}"},
                status=TaskStatus.COMPLETED,
            )
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 添加2个任务到L2
        for i in range(2):
            task = Task(
                task_id=f"l2-task-{i}",
                action="execute",
                parameters={"content": f"L2 Task {i}"},
                status=TaskStatus.COMPLETED,
            )
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        # 3. 获取统计信息
        stats = memory.get_stats()

        # 4. 验证统计信息
        assert "l1_size" in stats, "Expected l1_size in stats"
        assert "l2_size" in stats, "Expected l2_size in stats"
        assert "max_l1_size" in stats, "Expected max_l1_size in stats"
        assert "max_l2_size" in stats, "Expected max_l2_size in stats"

        # 5. 验证数值正确
        assert stats["l1_size"] == 3, f"Expected 3 tasks in L1, got {stats['l1_size']}"
        assert stats["l2_size"] == 2, f"Expected 2 tasks in L2, got {stats['l2_size']}"
        assert stats["max_l1_size"] == 5, f"Expected max_l1_size=5, got {stats['max_l1_size']}"
        assert stats["max_l2_size"] == 3, f"Expected max_l2_size=3, got {stats['max_l2_size']}"

        print(
            f"\n[SUCCESS] Memory stats: L1={stats['l1_size']}/{stats['max_l1_size']}, L2={stats['l2_size']}/{stats['max_l2_size']}"
        )


class TestMemoryRetrieval:
    """测试记忆调取功能"""

    @pytest.mark.asyncio
    async def test_retrieve_task_by_id(self):
        """测试通过task_id检索任务"""
        # 1. 创建LoomMemory并添加任务
        memory = LoomMemory(node_id="test-node")

        task = Task(
            task_id="test-task-123",
            action="execute",
            parameters={"content": "Test task"},
            status=TaskStatus.COMPLETED,
            result={"content": "Test result"},
        )
        memory.add_task(task)

        # 2. 通过task_id检索任务
        retrieved_task = memory.get_task("test-task-123")

        # 3. 验证检索到的任务
        assert retrieved_task is not None, "Expected to retrieve task"
        assert retrieved_task.task_id == "test-task-123"
        assert retrieved_task.parameters["content"] == "Test task"
        assert retrieved_task.result["content"] == "Test result"

        print(f"\n[SUCCESS] Retrieved task by ID: {retrieved_task.task_id}")

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_task(self):
        """测试检索不存在的任务"""
        # 1. 创建空的LoomMemory
        memory = LoomMemory(node_id="test-node")

        # 2. 尝试检索不存在的任务
        retrieved_task = memory.get_task("nonexistent-task")

        # 3. 验证返回None
        assert retrieved_task is None, "Expected None for nonexistent task"

        print("\n[SUCCESS] Correctly returned None for nonexistent task")

    @pytest.mark.asyncio
    async def test_retrieve_from_different_tiers(self):
        """测试从不同层级检索任务"""
        # 1. 创建LoomMemory
        memory = LoomMemory(node_id="test-node")

        # 2. 添加任务到不同层级
        l1_task = Task(
            task_id="l1-task",
            action="execute",
            parameters={"content": "L1 task"},
            status=TaskStatus.COMPLETED,
        )
        memory.add_task(l1_task, tier=MemoryTier.L1_RAW_IO)

        l2_task = Task(
            task_id="l2-task",
            action="execute",
            parameters={"content": "L2 task"},
            status=TaskStatus.COMPLETED,
        )
        memory.add_task(l2_task, tier=MemoryTier.L2_WORKING)

        # 3. 检索不同层级的任务
        retrieved_l1 = memory.get_task("l1-task")
        retrieved_l2 = memory.get_task("l2-task")

        # 4. 验证都能检索到
        assert retrieved_l1 is not None, "Expected to retrieve L1 task"
        assert retrieved_l1.task_id == "l1-task"

        assert retrieved_l2 is not None, "Expected to retrieve L2 task"
        assert retrieved_l2.task_id == "l2-task"

        print("\n[SUCCESS] Retrieved tasks from different tiers: L1 and L2")


class TestFractalMemory:
    """测试分形架构的记忆继承和同步"""

    @pytest.mark.asyncio
    async def test_agent_stores_task_in_memory(self):
        """测试Agent执行任务后将任务存储到记忆中"""
        from loom.orchestration.agent import Agent
        from loom.providers.llm.mock import MockLLMProvider
        from loom.tools.registry import ToolRegistry

        # 1. 创建工具注册表
        tool_registry = ToolRegistry()

        async def simple_tool(data: str) -> str:
            return f"Processed: {data}"

        tool_registry.register_function(simple_tool)

        # 2. 创建MockLLM
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "Processing..."},
                {"type": "tool_call", "name": "simple_tool", "arguments": {"data": "test"}},
                {"type": "text", "content": "Done"},
                {"type": "tool_call", "name": "done", "arguments": {"message": "Complete"}},
            ]
        )

        # 3. 创建Agent
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "simple_tool",
                    "description": "Process data",
                    "parameters": {
                        "type": "object",
                        "properties": {"data": {"type": "string"}},
                        "required": ["data"],
                    },
                },
            }
        ]

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=tools,
            require_done_tool=True,
            max_iterations=3,
        )

        # 4. 执行任务
        task = Task(
            task_id="memory-test-task",
            action="execute",
            parameters={"content": "Test memory storage"},
        )

        result = await agent.execute_task(task)

        # 5. 验证任务被存储到记忆中
        assert result.status == TaskStatus.COMPLETED

        # 从Agent的memory中检索任务
        stored_task = agent.memory.get_task("memory-test-task")
        assert stored_task is not None, "Expected task to be stored in memory"
        assert stored_task.task_id == "memory-test-task"
        assert stored_task.status == TaskStatus.COMPLETED

        print(f"\n[SUCCESS] Agent stored task in memory: {stored_task.task_id}")

    @pytest.mark.asyncio
    async def test_child_node_inherits_parent_memory(self):
        """测试子节点继承父节点的记忆"""
        from loom.fractal.memory import FractalMemory
        from loom.orchestration.agent import Agent
        from loom.providers.llm.mock import MockLLMProvider
        from loom.tools.registry import ToolRegistry

        # 1. 创建父Agent
        tool_registry = ToolRegistry()
        llm = MockLLMProvider()

        parent_agent = Agent(
            node_id="parent-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=[],
            require_done_tool=False,
        )

        # 2. 在父Agent的记忆中添加一些任务
        parent_task = Task(
            task_id="parent-task-1",
            action="execute",
            parameters={"content": "Parent task"},
            status=TaskStatus.COMPLETED,
            result={"content": "Parent result"},
        )
        parent_agent.memory.add_task(parent_task, tier=MemoryTier.L2_WORKING)

        # 3. 创建FractalMemory给父Agent
        parent_fractal_memory = FractalMemory(
            node_id="parent-agent",
            parent_memory=None,
            base_memory=parent_agent.memory,
        )
        parent_agent.fractal_memory = parent_fractal_memory

        # 4. 创建子任务
        child_task = Task(
            task_id="child-task-1",
            action="execute",
            parameters={"content": "Child task"},
        )

        # 5. 使用_create_child_node创建子节点
        child_agent = await parent_agent._create_child_node(
            subtask=child_task,
            context_hints=[],
        )

        # 6. 验证子节点有fractal_memory
        assert hasattr(child_agent, "fractal_memory"), "Expected child to have fractal_memory"
        assert child_agent.fractal_memory is not None

        # 7. 验证子节点的fractal_memory有parent_memory引用
        assert (
            child_agent.fractal_memory.parent_memory is not None
        ), "Expected child to have parent_memory reference"

        print("\n[SUCCESS] Child node inherited parent memory structure")

    @pytest.mark.asyncio
    async def test_child_memory_syncs_back_to_parent(self):
        """测试子节点记忆同步回父节点"""
        from loom.fractal.memory import FractalMemory, MemoryScope
        from loom.orchestration.agent import Agent
        from loom.providers.llm.mock import MockLLMProvider
        from loom.tools.registry import ToolRegistry

        # 1. 创建父Agent
        tool_registry = ToolRegistry()
        llm = MockLLMProvider()

        parent_agent = Agent(
            node_id="parent-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=[],
            require_done_tool=False,
        )

        # 2. 创建FractalMemory给父Agent
        parent_fractal_memory = FractalMemory(
            node_id="parent-agent",
            parent_memory=None,
            base_memory=parent_agent.memory,
        )
        parent_agent.fractal_memory = parent_fractal_memory

        # 3. 创建子任务
        child_task = Task(
            task_id="child-task-sync",
            action="execute",
            parameters={"content": "Child task for sync test"},
        )

        # 4. 创建子节点
        child_agent = await parent_agent._create_child_node(
            subtask=child_task,
            context_hints=[],
        )

        # 5. 在子节点的记忆中添加一个任务（模拟子节点执行任务）
        child_completed_task = Task(
            task_id="child-completed-task",
            action="execute",
            parameters={"content": "Task completed by child"},
            status=TaskStatus.COMPLETED,
            result={"content": "Child result"},
        )
        child_agent.memory.add_task(child_completed_task)

        # 6. 将子节点的记忆写入SHARED scope（这样才能同步回父节点）
        # 注意：在实际使用中，子节点会自动将重要信息写入SHARED scope
        if hasattr(child_agent, "fractal_memory") and child_agent.fractal_memory:
            await child_agent.fractal_memory.write(
                "child-shared-info",
                {"task_id": "child-completed-task", "result": "Child result"},
                MemoryScope.SHARED,
            )

        # 7. 同步子节点记忆回父节点
        await parent_agent._sync_memory_from_child(child_agent)

        # 8. 验证父节点的fractal_memory中包含子节点的SHARED记忆
        if hasattr(parent_agent, "fractal_memory") and parent_agent.fractal_memory:
            parent_shared = await parent_agent.fractal_memory.list_by_scope(MemoryScope.SHARED)

            # 验证至少有一条SHARED记忆
            assert len(parent_shared) > 0, "Expected parent to have SHARED memories from child"

            # 验证包含子节点写入的信息
            shared_ids = [entry.id for entry in parent_shared]
            assert (
                "child-shared-info" in shared_ids
            ), "Expected child's shared info in parent memory"

        print(
            f"\n[SUCCESS] Child memory synced back to parent - {len(parent_shared)} shared entries"
        )
