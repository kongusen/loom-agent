"""
EventBus Hierarchy Tests

测试事件总线层级功能
"""

import pytest

from loom.events.event_bus import EventBus
from loom.protocol import Task, TaskStatus


class TestEventBusHierarchy:
    """测试EventBus的层级功能"""

    def test_create_child_bus(self):
        """测试创建子级事件总线"""
        parent = EventBus()
        child = parent.create_child_bus("child_node")

        assert child.node_id == "child_node"
        assert child.parent_bus is parent

    def test_create_child_bus_inherits_debug_mode(self):
        """测试子级总线继承调试模式"""
        parent = EventBus(debug_mode=True)
        child = parent.create_child_bus("child_node")

        assert child._recent_events is not None
        assert child._recent_events.maxlen == 100

    def test_create_nested_child_buses(self):
        """测试创建嵌套的子级总线（分形结构）"""
        root = EventBus(node_id="root")
        level1 = root.create_child_bus("level1")
        level2 = level1.create_child_bus("level2")

        assert level2.node_id == "level2"
        assert level2.parent_bus is level1
        assert level1.parent_bus is root

    @pytest.mark.asyncio
    async def test_child_bus_propagates_to_parent(self):
        """测试子级总线事件传播到父级"""
        parent = EventBus()
        child = parent.create_child_bus("child_node")

        received_by_parent = []

        async def parent_handler(task: Task) -> Task:
            received_by_parent.append(task.task_id)
            return task

        parent.register_handler("*", parent_handler)

        # 在子级发布事件
        task = Task(task_id="child_task", action="test_action", status=TaskStatus.PENDING)
        await child.publish(task)

        # 等待异步传播
        import asyncio
        await asyncio.sleep(0.05)

        # 父级应该收到事件
        assert "child_task" in received_by_parent

    @pytest.mark.asyncio
    async def test_multiple_child_buses_concurrent(self):
        """测试多个子级总线并发不冲突"""
        parent = EventBus()
        child1 = parent.create_child_bus("child1")
        child2 = parent.create_child_bus("child2")

        received_by_parent = []

        async def parent_handler(task: Task) -> Task:
            received_by_parent.append(task.task_id)
            return task

        parent.register_handler("*", parent_handler)

        # 并发发布
        import asyncio
        task1 = Task(task_id="task_from_child1", action="action1")
        task2 = Task(task_id="task_from_child2", action="action2")

        await asyncio.gather(
            child1.publish(task1),
            child2.publish(task2),
        )

        await asyncio.sleep(0.05)

        # 父级应该收到两个事件
        assert "task_from_child1" in received_by_parent
        assert "task_from_child2" in received_by_parent

    @pytest.mark.asyncio
    async def test_three_level_propagation(self):
        """测试三层级事件传播（分形自相似验证）"""
        root = EventBus()
        level1 = root.create_child_bus("level1")
        level2 = level1.create_child_bus("level2")

        received_by_root = []

        async def root_handler(task: Task) -> Task:
            received_by_root.append(task.task_id)
            return task

        root.register_handler("*", root_handler)

        # 在最深层发布事件
        task = Task(task_id="deep_task", action="action")
        await level2.publish(task)

        import asyncio
        await asyncio.sleep(0.1)  # 等待两层传播

        # 根级应该收到事件
        assert "deep_task" in received_by_root

    @pytest.mark.asyncio
    async def test_parent_handler_error_does_not_affect_child(self):
        """测试父级处理器异常不影响子级"""
        parent = EventBus()
        child = parent.create_child_bus("child")

        async def failing_parent_handler(task: Task) -> Task:
            raise ValueError("Parent handler failed")

        parent.register_handler("*", failing_parent_handler)

        # 子级发布应该正常完成
        task = Task(task_id="task1", action="action", status=TaskStatus.PENDING)
        result = await child.publish(task)

        # 子级不应该报错
        assert result.status == TaskStatus.PENDING
        assert result.error is None

    def test_node_id_property(self):
        """测试node_id属性"""
        bus = EventBus(node_id="my_node")
        assert bus.node_id == "my_node"

    def test_parent_bus_property(self):
        """测试parent_bus属性"""
        parent = EventBus()
        child = parent.create_child_bus("child")
        
        assert parent.parent_bus is None
        assert child.parent_bus is parent
