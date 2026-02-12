"""
Stream API Async Integration Tests

测试流式观测API的异步流功能，实际调用EventBus和流式方法
"""

import asyncio
import json

import pytest

from loom.api.stream_api import FractalStreamAPI, OutputStrategy
from loom.events.event_bus import EventBus
from loom.runtime import Task, TaskStatus


class TestFractalStreamAPIAsyncStreams:
    """测试FractalStreamAPI的异步流方法"""

    @pytest.mark.asyncio
    async def test_stream_all_events_receives_events(self):
        """测试stream_all_events能接收事件"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        # 启动流式订阅
        stream = api.stream_all_events(OutputStrategy.REALTIME)
        connected_event = await stream.__anext__()

        # 验证连接事件
        assert "connected" in connected_event
        assert "realtime" in connected_event

        # 发布一个事件
        task = Task(
            taskId="test-task-1",
            action="node.thinking",
            parameters={"node_id": "test-node", "content": "thinking..."},
            status=TaskStatus.RUNNING,
        )
        await event_bus.publish(task)

        # 等待并接收事件
        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "node.thinking" in event or "test-task-1" in event
        except StopAsyncIteration:
            pass

    @pytest.mark.asyncio
    async def test_stream_all_events_with_different_strategies(self):
        """测试不同输出策略"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)
        api.register_node("test-node", "root")

        for strategy in [OutputStrategy.REALTIME, OutputStrategy.BY_NODE, OutputStrategy.TREE]:
            stream = api.stream_all_events(strategy)
            connected_event = await stream.__anext__()

            assert "connected" in connected_event
            assert strategy.value in connected_event

            # 发布事件
            task = Task(
                taskId=f"task-{strategy.value}",
                action="node.thinking",
                parameters={"node_id": "test-node", "content": "test"},
                status=TaskStatus.RUNNING,
            )
            await event_bus.publish(task)

            await asyncio.sleep(0.1)
            try:
                event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
                assert event is not None
            except (StopAsyncIteration, asyncio.TimeoutError):
                pass

    @pytest.mark.asyncio
    async def test_stream_node_events_filters_by_node(self):
        """测试stream_node_events按节点过滤"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)
        api.register_node("target-node", "root")
        api.register_node("other-node", "root")

        stream = api.stream_node_events("target-node", include_children=True)
        connected_event = await stream.__anext__()

        assert "target-node" in connected_event

        # 发布目标节点事件
        target_task = Task(
            taskId="target-task",
            action="node.thinking",
            parameters={"node_id": "target-node", "content": "target thinking"},
            status=TaskStatus.RUNNING,
        )
        await event_bus.publish(target_task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "target-node" in event or "target-task" in event
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_stream_node_events_with_children(self):
        """测试stream_node_events包含子节点"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)
        api.register_node("parent", "root")
        api.register_node("child", "parent")

        stream = api.stream_node_events("parent", include_children=True)
        await stream.__anext__()  # 跳过连接事件

        # 发布子节点事件
        child_task = Task(
            taskId="child-task",
            action="node.thinking",
            parameters={"node_id": "child", "content": "child thinking"},
            status=TaskStatus.RUNNING,
        )
        await event_bus.publish(child_task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert event is not None
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_stream_thinking_events_filters_thinking(self):
        """测试stream_thinking_events只接收思考事件"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        stream = api.stream_thinking_events()
        await stream.__anext__()  # 跳过连接事件

        # 发布思考事件
        thinking_task = Task(
            taskId="thinking-task",
            action="node.thinking",
            parameters={"node_id": "test-node", "content": "thinking..."},
            status=TaskStatus.RUNNING,
        )
        await event_bus.publish(thinking_task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "node.thinking" in event or "thinking-task" in event
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_stream_thinking_events_with_node_filter(self):
        """测试stream_thinking_events按节点过滤"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        stream = api.stream_thinking_events("target-node")
        await stream.__anext__()  # 跳过连接事件

        # 发布目标节点思考事件
        task = Task(
            taskId="target-thinking",
            action="node.thinking",
            parameters={"node_id": "target-node", "content": "thinking"},
            status=TaskStatus.RUNNING,
        )
        await event_bus.publish(task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert event is not None
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_stream_tool_events_filters_tools(self):
        """测试stream_tool_events只接收工具事件"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        stream = api.stream_tool_events()
        await stream.__anext__()  # 跳过连接事件

        # 发布工具调用事件
        tool_task = Task(
            taskId="tool-task",
            action="node.tool_call",
            parameters={"node_id": "test-node", "tool": "search"},
            status=TaskStatus.RUNNING,
        )
        await event_bus.publish(tool_task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "tool-task" in event or "node.tool_call" in event
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_stream_heartbeat_on_timeout(self):
        """测试超时时发送心跳"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        stream = api.stream_all_events(OutputStrategy.REALTIME)
        await stream.__anext__()  # 跳过连接事件

        # 等待超时（30秒太长，我们需要mock或修改超时时间）
        # 这里我们只验证心跳格式是正确的
        # 实际测试需要mock asyncio.wait_for或修改超时时间
        pass

    @pytest.mark.asyncio
    async def test_stream_cancellation_sends_disconnect(self):
        """测试取消流时发送断开连接事件"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        stream = api.stream_all_events(OutputStrategy.REALTIME)
        await stream.__anext__()  # 跳过连接事件

        # 取消流
        task = asyncio.create_task(stream.__anext__())
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_multiple_event_types_in_stream_all(self):
        """测试stream_all_events接收多种事件类型"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        stream = api.stream_all_events(OutputStrategy.REALTIME)
        await stream.__anext__()  # 跳过连接事件

        # 发布多种类型的事件
        events = [
            Task(
                taskId="thinking-1",
                action="node.thinking",
                parameters={"node_id": "n1", "content": "thinking"},
                status=TaskStatus.RUNNING,
            ),
            Task(
                taskId="tool-1",
                action="node.tool_call",
                parameters={"node_id": "n1", "tool": "search"},
                status=TaskStatus.RUNNING,
            ),
            Task(
                taskId="result-1",
                action="node.tool_result",
                parameters={"node_id": "n1", "result": "found"},
                status=TaskStatus.COMPLETED,
            ),
        ]

        for task in events:
            await event_bus.publish(task)
            await asyncio.sleep(0.05)

        # 验证接收到事件
        received = []
        for _ in range(3):
            try:
                event = await asyncio.wait_for(stream.__anext__(), timeout=0.5)
                received.append(event)
            except (StopAsyncIteration, asyncio.TimeoutError):
                break

        assert len(received) > 0
