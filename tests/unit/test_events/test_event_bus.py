"""
Event Bus Unit Tests

测试事件总线的核心功能
"""

from unittest.mock import AsyncMock, Mock

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
        """测试发布任务但无处理器 - EventBus不修改状态"""
        bus = EventBus()
        task = Task(task_id="task1", action="unknown_action", status=TaskStatus.PENDING)

        result = await bus.publish(task)

        # EventBus 不修改状态，返回原始任务
        assert result.status == TaskStatus.PENDING
        assert result.task_id == "task1"

    @pytest.mark.asyncio
    async def test_publish_with_handler_success(self):
        """测试发布任务并成功执行 - handler决定状态"""
        bus = EventBus()

        async def handler(task: Task) -> Task:
            task.result = {"data": "success"}
            task.status = TaskStatus.COMPLETED  # handler 设置状态
            return task

        bus.register_handler("test_action", handler)
        task = Task(task_id="task1", action="test_action")

        result = await bus.publish(task)

        # EventBus 保留 handler 返回的状态
        assert result.status == TaskStatus.COMPLETED
        assert result.result["data"] == "success"

    @pytest.mark.asyncio
    async def test_publish_with_handler_error(self):
        """测试处理器执行失败 - EventBus只设置error，不修改status"""
        bus = EventBus()

        async def failing_handler(task: Task) -> Task:
            raise ValueError("Handler failed")

        bus.register_handler("test_action", failing_handler)
        task = Task(task_id="task1", action="test_action", status=TaskStatus.PENDING)

        result = await bus.publish(task)

        # EventBus 不修改状态，只设置错误信息
        assert result.status == TaskStatus.PENDING
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
        """测试通过transport发布任务 - EventBus不修改状态"""
        mock_transport = Mock()
        mock_transport.connect = AsyncMock()
        mock_transport.publish = AsyncMock()
        mock_transport.is_connected = Mock(return_value=True)

        bus = EventBus(transport=mock_transport)
        bus._transport_initialized = True

        task = Task(task_id="task1", action="test_action", parameters={"key": "value"}, status=TaskStatus.PENDING)
        result = await bus.publish(task)

        # 应该通过transport发布
        mock_transport.publish.assert_called_once()
        call_args = mock_transport.publish.call_args
        assert call_args[0][0] == "task.test_action"  # topic
        assert b"taskId" in call_args[0][1]  # task_json encoded (camelCase)

        # EventBus 不修改状态，返回原始任务
        assert result.status == TaskStatus.PENDING

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
        """测试fire-and-forget模式 - EventBus不修改状态"""
        bus = EventBus()

        executed = []

        async def handler(task: Task) -> Task:
            executed.append(task.task_id)
            task.result = {"done": True}
            return task

        bus.register_handler("test_action", handler)
        task = Task(task_id="task1", action="test_action", status=TaskStatus.PENDING)

        # 使用fire-and-forget模式
        result = await bus.publish(task, wait_result=False)

        # EventBus 不修改状态，返回原始任务
        assert result.status == TaskStatus.PENDING
        # 但handler会被异步执行
        import asyncio

        await asyncio.sleep(0.01)  # 等待异步执行
        assert "task1" in executed

    @pytest.mark.asyncio
    async def test_publish_fire_and_forget_with_handler_error(self):
        """测试fire-and-forget模式时处理器错误不影响返回 - EventBus不修改状态"""
        bus = EventBus()

        async def failing_handler(task: Task) -> Task:
            raise ValueError("Handler error")

        bus.register_handler("test_action", failing_handler)
        task = Task(task_id="task1", action="test_action", status=TaskStatus.PENDING)

        # fire-and-forget模式不会抛出异常
        result = await bus.publish(task, wait_result=False)

        # EventBus 不修改状态，返回原始任务（尽管handler会失败）
        assert result.status == TaskStatus.PENDING


class TestEventBusWildcardSubscription:
    """测试EventBus的通配符订阅功能"""

    @pytest.mark.asyncio
    async def test_wildcard_subscription_receives_all_tasks(self):
        """测试通配符订阅可以接收所有任务"""
        bus = EventBus()

        received_tasks = []

        async def wildcard_handler(task: Task) -> Task:
            received_tasks.append(task.task_id)
            return task

        async def specific_handler(task: Task) -> Task:
            task.status = TaskStatus.COMPLETED
            return task

        # 注册通配符订阅者
        bus.register_handler("*", wildcard_handler)
        # 注册特定动作处理器
        bus.register_handler("test_action", specific_handler)

        # 发布任务
        task1 = Task(task_id="task1", action="test_action")
        task2 = Task(task_id="task2", action="another_action")

        await bus.publish(task1)
        await bus.publish(task2)

        # 等待异步通知完成
        import asyncio
        await asyncio.sleep(0.01)

        # 通配符订阅者应该接收到所有任务
        assert "task1" in received_tasks
        assert "task2" in received_tasks

    @pytest.mark.asyncio
    async def test_wildcard_handler_error_does_not_affect_main_flow(self):
        """测试通配符处理器异常不影响主流程"""
        bus = EventBus()

        async def failing_wildcard_handler(task: Task) -> Task:
            raise ValueError("Wildcard handler error")

        async def specific_handler(task: Task) -> Task:
            task.status = TaskStatus.COMPLETED
            task.result = {"success": True}
            return task

        bus.register_handler("*", failing_wildcard_handler)
        bus.register_handler("test_action", specific_handler)

        task = Task(task_id="task1", action="test_action")
        result = await bus.publish(task)

        # 主流程应该正常完成，不受通配符处理器异常影响
        assert result.status == TaskStatus.COMPLETED
        assert result.result["success"] is True


class TestEventBusDebugMode:
    """测试EventBus的调试模式"""

    def test_debug_mode_enabled(self):
        """测试启用调试模式"""
        bus = EventBus(debug_mode=True)

        assert bus._recent_events is not None
        assert hasattr(bus._recent_events, "maxlen")
        assert bus._recent_events.maxlen == 100

    def test_debug_mode_disabled(self):
        """测试禁用调试模式（默认）"""
        bus = EventBus(debug_mode=False)

        assert bus._recent_events is None

    @pytest.mark.asyncio
    async def test_debug_mode_records_events(self):
        """测试调试模式记录事件"""
        bus = EventBus(debug_mode=True)

        async def handler(task: Task) -> Task:
            task.status = TaskStatus.COMPLETED
            return task

        bus.register_handler("test_action", handler)

        # 发布多个任务
        for i in range(5):
            task = Task(task_id=f"task{i}", action="test_action")
            await bus.publish(task)

        # 获取最近的事件
        recent_events = bus.get_recent_events(limit=10)

        assert len(recent_events) == 5
        assert recent_events[0].task_id == "task0"
        assert recent_events[4].task_id == "task4"

    @pytest.mark.asyncio
    async def test_debug_mode_respects_maxlen(self):
        """测试调试模式遵守最大长度限制"""
        bus = EventBus(debug_mode=True)

        async def handler(task: Task) -> Task:
            return task

        bus.register_handler("test_action", handler)

        # 发布超过maxlen的任务
        for i in range(150):
            task = Task(task_id=f"task{i}", action="test_action")
            await bus.publish(task)

        # 应该只保留最近的100条
        recent_events = bus.get_recent_events(limit=200)
        assert len(recent_events) == 100
        # 最旧的应该是task50（0-49被驱逐）
        assert recent_events[0].task_id == "task50"
        assert recent_events[-1].task_id == "task149"

    @pytest.mark.asyncio
    async def test_get_recent_events_without_debug_mode(self):
        """测试未启用调试模式时获取事件返回空列表"""
        bus = EventBus(debug_mode=False)

        async def handler(task: Task) -> Task:
            return task

        bus.register_handler("test_action", handler)

        task = Task(task_id="task1", action="test_action")
        await bus.publish(task)

        # 未启用调试模式，应该返回空列表
        recent_events = bus.get_recent_events()
        assert recent_events == []

