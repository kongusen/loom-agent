"""
Event Bus Unit Tests

测试事件总线的核心功能
"""

from unittest.mock import AsyncMock, Mock, patch

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


class TestEventBusPublishWithTransport:
    """测试EventBus的transport模式"""

    @pytest.mark.asyncio
    async def test_publish_with_transport_connects_on_first_publish(self):
        """测试首次发布时transport会自动连接（触发lines 54-55）"""
        mock_transport = Mock()
        mock_transport.connect = AsyncMock()
        mock_transport.publish = AsyncMock()
        mock_transport.is_connected = Mock(return_value=False)

        bus = EventBus(transport=mock_transport)
        assert bus._transport_initialized is False

        task = Task(task_id="task1", action="test_action")
        await bus.publish(task)

        # transport应该已连接
        mock_transport.connect.assert_called_once()
        assert bus._transport_initialized is True

    @pytest.mark.asyncio
    async def test_publish_with_transport_sends_via_transport(self):
        """测试通过transport发布任务（触发lines 92-95）"""
        mock_transport = Mock()
        mock_transport.connect = AsyncMock()
        mock_transport.publish = AsyncMock()
        mock_transport.is_connected = Mock(return_value=True)

        bus = EventBus(transport=mock_transport)
        bus._transport_initialized = True

        task = Task(task_id="task1", action="test_action", parameters={"key": "value"})
        result = await bus.publish(task)

        # 应该通过transport发布
        mock_transport.publish.assert_called_once()
        call_args = mock_transport.publish.call_args
        assert call_args[0][0] == "task.test_action"  # topic
        assert b"taskId" in call_args[0][1]  # task_json encoded (camelCase)

        # 任务应该返回RUNNING状态（分布式模式）
        assert result.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_publish_with_transport_reuses_connection(self):
        """测试transport连接复用"""
        mock_transport = Mock()
        mock_transport.connect = AsyncMock()
        mock_transport.publish = AsyncMock()
        mock_transport.is_connected = Mock(return_value=True)

        bus = EventBus(transport=mock_transport)
        bus._transport_initialized = True

        # 发布多个任务
        for i in range(3):
            task = Task(task_id=f"task{i}", action="test_action")
            await bus.publish(task)

        # connect应该只被调用一次（因为已设置transport_initialized）
        assert mock_transport.connect.call_count == 0


class TestEventBusFireAndForgetError:
    """测试EventBus的fire-and-forget模式"""

    @pytest.mark.asyncio
    async def test_publish_fire_and_forget_mode(self):
        """测试fire-and-forget模式（触发lines 108-113）"""
        bus = EventBus()

        executed = []

        async def handler(task: Task) -> Task:
            executed.append(task.task_id)
            task.result = {"done": True}
            return task

        bus.register_handler("test_action", handler)
        task = Task(task_id="task1", action="test_action")

        # 使用fire-and-forget模式
        result = await bus.publish(task, wait_result=False)

        # 任务应该立即返回RUNNING状态
        assert result.status == TaskStatus.RUNNING
        # 但handler会被异步执行
        import asyncio

        await asyncio.sleep(0.01)  # 等待异步执行
        assert "task1" in executed

    @pytest.mark.asyncio
    async def test_publish_fire_and_forget_with_handler_error(self):
        """测试fire-and-forget模式时处理器错误不影响返回"""
        bus = EventBus()

        async def failing_handler(task: Task) -> Task:
            raise ValueError("Handler error")

        bus.register_handler("test_action", failing_handler)
        task = Task(task_id="task1", action="test_action")

        # fire-and-forget模式不会抛出异常
        result = await bus.publish(task, wait_result=False)

        # 任务应该立即返回RUNNING状态（尽管handler会失败）
        assert result.status == TaskStatus.RUNNING

