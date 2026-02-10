"""
Runtime Components Unit Tests

测试Dispatcher和Interceptor的核心功能
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.events import EventBus
from loom.runtime import Task, TaskStatus
from loom.runtime.dispatcher import Dispatcher


class TestDispatcherInit:
    """测试Dispatcher初始化"""

    def test_init(self):
        """测试初始化"""
        event_bus = EventBus()
        dispatcher = Dispatcher(event_bus)

        assert dispatcher.event_bus == event_bus
        assert dispatcher.nodes == {}


class TestDispatcherNodeManagement:
    """测试Dispatcher节点管理"""

    def test_register_node(self):
        """测试注册节点"""
        event_bus = EventBus()
        dispatcher = Dispatcher(event_bus)

        mock_node = Mock()
        mock_node.node_id = "node_1"

        dispatcher.register_node(mock_node)

        assert "node_1" in dispatcher.nodes
        assert dispatcher.nodes["node_1"] == mock_node

    def test_register_multiple_nodes(self):
        """测试注册多个节点"""
        event_bus = EventBus()
        dispatcher = Dispatcher(event_bus)

        mock_node1 = Mock()
        mock_node1.node_id = "node_1"
        mock_node2 = Mock()
        mock_node2.node_id = "node_2"

        dispatcher.register_node(mock_node1)
        dispatcher.register_node(mock_node2)

        assert len(dispatcher.nodes) == 2
        assert "node_1" in dispatcher.nodes
        assert "node_2" in dispatcher.nodes

    def test_unregister_node_success(self):
        """测试成功注销节点"""
        event_bus = EventBus()
        dispatcher = Dispatcher(event_bus)

        mock_node = Mock()
        mock_node.node_id = "node_1"
        dispatcher.register_node(mock_node)

        result = dispatcher.unregister_node("node_1")

        assert result is True
        assert "node_1" not in dispatcher.nodes

    def test_unregister_node_not_found(self):
        """测试注销不存在的节点"""
        event_bus = EventBus()
        dispatcher = Dispatcher(event_bus)

        result = dispatcher.unregister_node("nonexistent")

        assert result is False


class TestDispatcherDispatch:
    """测试Dispatcher的dispatch方法"""

    @pytest.mark.asyncio
    async def test_dispatch_to_registered_node(self):
        """测试调度到已注册的节点"""
        event_bus = EventBus()
        dispatcher = Dispatcher(event_bus)

        # 创建mock节点
        mock_node = Mock()
        mock_node.node_id = "node_1"
        mock_node.execute_task = AsyncMock(
            return_value=Task(
                task_id="task_1",
                action="test",
                status=TaskStatus.COMPLETED,
                result={"data": "success"},
            )
        )

        dispatcher.register_node(mock_node)

        # 创建任务
        task = Task(task_id="task_1", action="test", target_agent="node_1")

        # 调度任务
        result = await dispatcher.dispatch(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result["data"] == "success"
        mock_node.execute_task.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_dispatch_to_event_bus(self):
        """测试调度到事件总线（节点不存在）"""
        event_bus = EventBus()
        event_bus.publish = AsyncMock(
            return_value=Task(task_id="task_1", action="test", status=TaskStatus.COMPLETED)
        )

        dispatcher = Dispatcher(event_bus)

        # 创建任务（目标节点不存在）
        task = Task(task_id="task_1", action="test", target_agent="nonexistent")

        # 调度任务
        result = await dispatcher.dispatch(task)

        assert result.status == TaskStatus.COMPLETED
        event_bus.publish.assert_called_once_with(task)


class TestInterceptor:
    """测试Interceptor基类"""

    @pytest.mark.asyncio
    async def test_before_default(self):
        """测试默认before方法"""
        from loom.runtime.interceptor import Interceptor

        interceptor = Interceptor()
        task = Task(task_id="task_1", action="test")

        result = await interceptor.before(task)

        assert result == task

    @pytest.mark.asyncio
    async def test_after_default(self):
        """测试默认after方法"""
        from loom.runtime.interceptor import Interceptor

        interceptor = Interceptor()
        task = Task(task_id="task_1", action="test")

        result = await interceptor.after(task)

        assert result == task


class TestInterceptorChain:
    """测试InterceptorChain"""

    def test_init(self):
        """测试初始化"""
        from loom.runtime.interceptor import InterceptorChain

        chain = InterceptorChain()

        assert chain.interceptors == []

    def test_add_interceptor(self):
        """测试添加拦截器"""
        from loom.runtime.interceptor import Interceptor, InterceptorChain

        chain = InterceptorChain()
        interceptor = Interceptor()

        chain.add(interceptor)

        assert len(chain.interceptors) == 1
        assert chain.interceptors[0] == interceptor

    def test_add_multiple_interceptors(self):
        """测试添加多个拦截器"""
        from loom.runtime.interceptor import Interceptor, InterceptorChain

        chain = InterceptorChain()
        interceptor1 = Interceptor()
        interceptor2 = Interceptor()

        chain.add(interceptor1)
        chain.add(interceptor2)

        assert len(chain.interceptors) == 2

    @pytest.mark.asyncio
    async def test_execute_no_interceptors(self):
        """测试无拦截器时执行"""
        from loom.runtime.interceptor import InterceptorChain

        chain = InterceptorChain()
        task = Task(task_id="task_1", action="test")

        async def mock_executor(t: Task) -> Task:
            t.status = TaskStatus.COMPLETED
            return t

        result = await chain.execute(task, mock_executor)

        assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_interceptors(self):
        """测试带拦截器执行"""
        from loom.runtime.interceptor import Interceptor, InterceptorChain

        # 创建自定义拦截器
        class TestInterceptor(Interceptor):
            def __init__(self, name: str):
                self.name = name
                self.before_called = False
                self.after_called = False

            async def before(self, task: Task) -> Task:
                self.before_called = True
                task.metadata[f"{self.name}_before"] = True
                return task

            async def after(self, task: Task) -> Task:
                self.after_called = True
                task.metadata[f"{self.name}_after"] = True
                return task

        chain = InterceptorChain()
        interceptor1 = TestInterceptor("int1")
        interceptor2 = TestInterceptor("int2")

        chain.add(interceptor1)
        chain.add(interceptor2)

        task = Task(task_id="task_1", action="test")

        async def mock_executor(t: Task) -> Task:
            t.status = TaskStatus.COMPLETED
            return t

        result = await chain.execute(task, mock_executor)

        # 验证拦截器被调用
        assert interceptor1.before_called
        assert interceptor1.after_called
        assert interceptor2.before_called
        assert interceptor2.after_called

        # 验证元数据
        assert result.metadata["int1_before"] is True
        assert result.metadata["int2_before"] is True
        assert result.metadata["int1_after"] is True
        assert result.metadata["int2_after"] is True

    @pytest.mark.asyncio
    async def test_execute_order(self):
        """测试拦截器执行顺序（before正序，after逆序）"""
        from loom.runtime.interceptor import Interceptor, InterceptorChain

        execution_order = []

        class OrderInterceptor(Interceptor):
            def __init__(self, name: str):
                self.name = name

            async def before(self, task: Task) -> Task:
                execution_order.append(f"{self.name}_before")
                return task

            async def after(self, task: Task) -> Task:
                execution_order.append(f"{self.name}_after")
                return task

        chain = InterceptorChain()
        chain.add(OrderInterceptor("A"))
        chain.add(OrderInterceptor("B"))
        chain.add(OrderInterceptor("C"))

        task = Task(task_id="task_1", action="test")

        async def mock_executor(t: Task) -> Task:
            execution_order.append("executor")
            return t

        await chain.execute(task, mock_executor)

        # 验证执行顺序：A_before, B_before, C_before, executor, C_after, B_after, A_after
        expected_order = [
            "A_before",
            "B_before",
            "C_before",
            "executor",
            "C_after",
            "B_after",
            "A_after",
        ]
        assert execution_order == expected_order
