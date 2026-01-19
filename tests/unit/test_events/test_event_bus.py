"""
Event Bus Unit Tests

测试事件总线的核心功能
"""

from unittest.mock import Mock

import pytest

from loom.events.event_bus import EventBus
from loom.protocol import Task, TaskStatus


class TestEventBusInit:
    """测试EventBus初始化"""

    def test_init_without_transport(self):
        """测试无transport初始化"""
        bus = EventBus()

        assert bus._handlers == {}
        assert bus._transport is None
        assert bus._transport_initialized is False

    def test_init_with_transport(self):
        """测试带transport初始化"""
        mock_transport = Mock()
        bus = EventBus(transport=mock_transport)

        assert bus._transport == mock_transport
        assert bus._transport_initialized is False


class TestEventBusRegisterHandler:
    """测试EventBus的register_handler方法"""

    def test_register_single_handler(self):
        """测试注册单个处理器"""
        bus = EventBus()

        async def handler(task: Task) -> Task:
            return task

        bus.register_handler("test_action", handler)

        assert "test_action" in bus._handlers
        assert len(bus._handlers["test_action"]) == 1
        assert bus._handlers["test_action"][0] == handler

    def test_register_multiple_handlers_same_action(self):
        """测试为同一action注册多个处理器"""
        bus = EventBus()

        async def handler1(task: Task) -> Task:
            return task

        async def handler2(task: Task) -> Task:
            return task

        bus.register_handler("test_action", handler1)
        bus.register_handler("test_action", handler2)

        assert len(bus._handlers["test_action"]) == 2


class TestEventBusPublish:
    """测试EventBus的publish方法"""

    @pytest.mark.asyncio
    async def test_publish_no_handler(self):
        """测试发布任务但无处理器"""
        bus = EventBus()
        task = Task(task_id="task1", action="unknown_action")

        result = await bus.publish(task)

        assert result.status == TaskStatus.FAILED
        assert "No handler found" in result.error

    @pytest.mark.asyncio
    async def test_publish_with_handler_success(self):
        """测试发布任务并成功执行"""
        bus = EventBus()

        async def handler(task: Task) -> Task:
            task.result = {"data": "success"}
            return task

        bus.register_handler("test_action", handler)
        task = Task(task_id="task1", action="test_action")

        result = await bus.publish(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result["data"] == "success"

    @pytest.mark.asyncio
    async def test_publish_with_handler_error(self):
        """测试处理器执行失败"""
        bus = EventBus()

        async def failing_handler(task: Task) -> Task:
            raise ValueError("Handler failed")

        bus.register_handler("test_action", failing_handler)
        task = Task(task_id="task1", action="test_action")

        result = await bus.publish(task)

        assert result.status == TaskStatus.FAILED
        assert "Handler failed" in result.error
