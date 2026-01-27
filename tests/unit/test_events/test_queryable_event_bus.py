"""
Queryable Event Bus Unit Tests

测试可查询事件总线的查询功能
"""

import pytest

from loom.events.queryable_event_bus import QueryableEventBus
from loom.protocol import Task


class TestQueryableEventBusInit:
    """测试 QueryableEventBus 初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        bus = QueryableEventBus()

        assert bus._event_history == []
        assert bus._events_by_node == {}
        assert bus._events_by_action == {}
        assert bus._events_by_task == {}
        assert bus._max_history == 1000

    def test_init_with_max_history(self):
        """测试带 max_history 初始化"""
        bus = QueryableEventBus(max_history=500)

        assert bus._max_history == 500


class TestQueryableEventBusPublish:
    """测试发布事件并记录到历史"""

    @pytest.mark.asyncio
    async def test_publish_records_event(self):
        """测试发布事件会记录到历史"""
        bus = QueryableEventBus()

        task = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"node_id": "node-1", "content": "思考内容"},
        )

        result = await bus.publish(task)

        assert len(bus._event_history) == 1
        assert bus._event_history[0] == result
        assert "node-1" in bus._events_by_node
        assert len(bus._events_by_node["node-1"]) == 1
        assert "node.thinking" in bus._events_by_action
        assert len(bus._events_by_action["node.thinking"]) == 1

    @pytest.mark.asyncio
    async def test_publish_records_with_parent_task_id(self):
        """测试发布带 parent_task_id 的事件"""
        bus = QueryableEventBus()

        task = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"node_id": "node-1", "parent_task_id": "parent-1"},
            parent_task_id="parent-1",
        )

        await bus.publish(task)

        assert "parent-1" in bus._events_by_task
        assert len(bus._events_by_task["parent-1"]) == 1

    @pytest.mark.asyncio
    async def test_publish_respects_max_history(self):
        """测试发布事件时限制历史大小"""
        bus = QueryableEventBus(max_history=3)

        # 发布超过限制的事件
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"node_id": f"node-{i}"},
            )
            await bus.publish(task)

        # 应该只保留最近3个
        assert len(bus._event_history) == 3
        assert bus._event_history[0].task_id == "task-2"
        assert bus._event_history[-1].task_id == "task-4"


class TestQueryableEventBusQueryByNode:
    """测试按节点查询"""

    @pytest.mark.asyncio
    async def test_query_by_node(self):
        """测试查询特定节点的事件"""
        bus = QueryableEventBus()

        # 发布多个节点的事件
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="node.thinking",
                parameters={"node_id": "node-1", "content": f"思考{i}"},
            )
            await bus.publish(task)

        # 查询 node-1 的事件
        events = bus.query_by_node("node-1")

        assert len(events) == 3
        assert all(e.parameters.get("node_id") == "node-1" for e in events)

    @pytest.mark.asyncio
    async def test_query_by_node_with_action_filter(self):
        """测试带动作过滤的节点查询"""
        bus = QueryableEventBus()

        # 发布不同类型的事件
        task1 = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"node_id": "node-1", "content": "思考"},
        )
        await bus.publish(task1)

        task2 = Task(
            task_id="task-2",
            action="node.tool_call",
            parameters={"node_id": "node-1", "tool_name": "test"},
        )
        await bus.publish(task2)

        # 只查询 thinking 事件
        events = bus.query_by_node("node-1", action_filter="node.thinking")

        assert len(events) == 1
        assert events[0].action == "node.thinking"

    @pytest.mark.asyncio
    async def test_query_by_node_with_limit(self):
        """测试带数量限制的节点查询"""
        bus = QueryableEventBus()

        # 发布多个事件
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="node.thinking",
                parameters={"node_id": "node-1", "content": f"思考{i}"},
            )
            await bus.publish(task)

        # 只查询最近2个
        events = bus.query_by_node("node-1", limit=2)

        assert len(events) == 2
        assert events[0].task_id == "task-3"
        assert events[1].task_id == "task-4"

    @pytest.mark.asyncio
    async def test_query_by_node_not_found(self):
        """测试查询不存在的节点"""
        bus = QueryableEventBus()

        events = bus.query_by_node("nonexistent-node")

        assert len(events) == 0


class TestQueryableEventBusQueryByAction:
    """测试按动作查询"""

    @pytest.mark.asyncio
    async def test_query_by_action(self):
        """测试查询特定动作的事件"""
        bus = QueryableEventBus()

        # 发布多个动作的事件
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="node.thinking",
                parameters={"node_id": f"node-{i}", "content": f"思考{i}"},
            )
            await bus.publish(task)

        # 查询 thinking 事件
        events = bus.query_by_action("node.thinking")

        assert len(events) == 3
        assert all(e.action == "node.thinking" for e in events)

    @pytest.mark.asyncio
    async def test_query_by_action_with_node_filter(self):
        """测试带节点过滤的动作查询"""
        bus = QueryableEventBus()

        # 发布不同节点的事件
        task1 = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"node_id": "node-1", "content": "思考1"},
        )
        await bus.publish(task1)

        task2 = Task(
            task_id="task-2",
            action="node.thinking",
            parameters={"node_id": "node-2", "content": "思考2"},
        )
        await bus.publish(task2)

        # 只查询 node-1 的 thinking 事件
        events = bus.query_by_action("node.thinking", node_filter="node-1")

        assert len(events) == 1
        assert events[0].parameters.get("node_id") == "node-1"

    @pytest.mark.asyncio
    async def test_query_by_action_with_limit(self):
        """测试带数量限制的动作查询"""
        bus = QueryableEventBus()

        # 发布多个事件
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="node.thinking",
                parameters={"node_id": f"node-{i}", "content": f"思考{i}"},
            )
            await bus.publish(task)

        # 只查询最近2个
        events = bus.query_by_action("node.thinking", limit=2)

        assert len(events) == 2


class TestQueryableEventBusQueryByTask:
    """测试按任务查询"""

    @pytest.mark.asyncio
    async def test_query_by_task(self):
        """测试查询特定任务的事件"""
        bus = QueryableEventBus()

        parent_task_id = "parent-task"

        # 发布多个属于同一父任务的事件
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="node.thinking",
                parameters={"node_id": "node-1", "parent_task_id": parent_task_id},
                parent_task_id=parent_task_id,
            )
            await bus.publish(task)

        # 查询父任务的所有事件
        events = bus.query_by_task(parent_task_id)

        assert len(events) == 3
        assert all(e.parameters.get("parent_task_id") == parent_task_id for e in events)

    @pytest.mark.asyncio
    async def test_query_by_task_with_action_filter(self):
        """测试带动作过滤的任务查询"""
        bus = QueryableEventBus()

        parent_task_id = "parent-task"

        # 发布不同类型的事件
        task1 = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"node_id": "node-1", "parent_task_id": parent_task_id},
            parent_task_id=parent_task_id,
        )
        await bus.publish(task1)

        task2 = Task(
            task_id="task-2",
            action="node.tool_call",
            parameters={"node_id": "node-1", "parent_task_id": parent_task_id},
            parent_task_id=parent_task_id,
        )
        await bus.publish(task2)

        # 只查询 thinking 事件
        events = bus.query_by_task(parent_task_id, action_filter="node.thinking")

        assert len(events) == 1
        assert events[0].action == "node.thinking"


class TestQueryableEventBusQueryRecent:
    """测试查询最近事件"""

    @pytest.mark.asyncio
    async def test_query_recent(self):
        """测试查询最近的事件"""
        bus = QueryableEventBus()

        # 发布多个事件
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"node_id": "node-1"},
            )
            await bus.publish(task)

        # 查询最近3个
        events = bus.query_recent(limit=3)

        assert len(events) == 3
        assert events[0].task_id == "task-2"
        assert events[-1].task_id == "task-4"

    @pytest.mark.asyncio
    async def test_query_recent_with_action_filter(self):
        """测试带动作过滤的最近事件查询"""
        bus = QueryableEventBus()

        # 发布不同类型的事件
        for i in range(3):
            task1 = Task(
                task_id=f"thinking-{i}",
                action="node.thinking",
                parameters={"node_id": "node-1"},
            )
            await bus.publish(task1)

            task2 = Task(
                task_id=f"tool-{i}",
                action="node.tool_call",
                parameters={"node_id": "node-1"},
            )
            await bus.publish(task2)

        # 只查询 thinking 事件
        events = bus.query_recent(limit=10, action_filter="node.thinking")

        assert len(events) == 3
        assert all(e.action == "node.thinking" for e in events)

    @pytest.mark.asyncio
    async def test_query_recent_with_node_filter(self):
        """测试带节点过滤的最近事件查询"""
        bus = QueryableEventBus()

        # 发布不同节点的事件
        for i in range(3):
            task1 = Task(
                task_id=f"node1-{i}",
                action="test_action",
                parameters={"node_id": "node-1"},
            )
            await bus.publish(task1)

            task2 = Task(
                task_id=f"node2-{i}",
                action="test_action",
                parameters={"node_id": "node-2"},
            )
            await bus.publish(task2)

        # 只查询 node-1 的事件
        events = bus.query_recent(limit=10, node_filter="node-1")

        assert len(events) == 3
        assert all(e.parameters.get("node_id") == "node-1" for e in events)


class TestQueryableEventBusQueryThinkingProcess:
    """测试查询思考过程"""

    @pytest.mark.asyncio
    async def test_query_thinking_process_by_node(self):
        """测试按节点查询思考过程"""
        bus = QueryableEventBus()

        # 发布思考事件
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="node.thinking",
                parameters={"node_id": "node-1", "content": f"思考{i}"},
            )
            await bus.publish(task)

        # 查询思考过程
        thoughts = bus.query_thinking_process(node_id="node-1", limit=10)

        assert len(thoughts) == 3
        assert "思考0" in thoughts
        assert "思考1" in thoughts
        assert "思考2" in thoughts

    @pytest.mark.asyncio
    async def test_query_thinking_process_by_task(self):
        """测试按任务查询思考过程"""
        bus = QueryableEventBus()

        parent_task_id = "parent-task"

        # 发布思考事件
        for i in range(2):
            task = Task(
                task_id=f"task-{i}",
                action="node.thinking",
                parameters={
                    "node_id": "node-1",
                    "content": f"思考{i}",
                    "parent_task_id": parent_task_id,
                },
                parent_task_id=parent_task_id,
            )
            await bus.publish(task)

        # 查询思考过程
        thoughts = bus.query_thinking_process(task_id=parent_task_id)

        assert len(thoughts) == 2

    @pytest.mark.asyncio
    async def test_query_thinking_process_all(self):
        """测试查询所有思考过程"""
        bus = QueryableEventBus()

        # 发布多个节点的思考事件
        for node_id in ["node-1", "node-2"]:
            for i in range(2):
                task = Task(
                    task_id=f"task-{node_id}-{i}",
                    action="node.thinking",
                    parameters={"node_id": node_id, "content": f"思考{node_id}-{i}"},
                )
                await bus.publish(task)

        # 查询所有思考过程
        thoughts = bus.query_thinking_process(limit=10)

        assert len(thoughts) == 4


class TestQueryableEventBusCollectiveMemory:
    """测试集体记忆"""

    @pytest.mark.asyncio
    async def test_get_collective_memory(self):
        """测试获取集体记忆"""
        bus = QueryableEventBus()

        # 发布多个节点的思考事件
        for node_id in ["node-1", "node-2"]:
            for i in range(2):
                task = Task(
                    task_id=f"task-{node_id}-{i}",
                    action="node.thinking",
                    parameters={"node_id": node_id, "content": f"思考{node_id}-{i}"},
                )
                await bus.publish(task)

        # 获取集体记忆
        memory = bus.get_collective_memory(limit=10)

        assert "node.thinking" in memory
        assert "node-1" in memory["node.thinking"]
        assert "node-2" in memory["node.thinking"]
        assert len(memory["node.thinking"]["node-1"]) == 2

    @pytest.mark.asyncio
    async def test_get_collective_memory_with_custom_actions(self):
        """测试获取指定动作类型的集体记忆"""
        bus = QueryableEventBus()

        # 发布不同类型的事件
        task1 = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"node_id": "node-1", "content": "思考"},
        )
        await bus.publish(task1)

        task2 = Task(
            task_id="task-2",
            action="node.tool_call",
            parameters={"node_id": "node-1", "tool_name": "test"},
        )
        await bus.publish(task2)

        # 只获取 tool_call 的集体记忆
        memory = bus.get_collective_memory(action_types=["node.tool_call"], limit=10)

        assert "node.tool_call" in memory
        assert "node.thinking" not in memory


class TestQueryableEventBusClearHistory:
    """测试清空历史"""

    @pytest.mark.asyncio
    async def test_clear_history(self):
        """测试清空历史记录"""
        bus = QueryableEventBus()

        # 发布一些事件
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"node_id": "node-1"},
            )
            await bus.publish(task)

        # 清空历史
        bus.clear_history()

        assert len(bus._event_history) == 0
        assert len(bus._events_by_node) == 0
        assert len(bus._events_by_action) == 0
        assert len(bus._events_by_task) == 0
