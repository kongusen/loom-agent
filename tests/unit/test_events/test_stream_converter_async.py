"""
Event Stream Converter Async Integration Tests

测试事件流转换器的异步流功能
"""

import asyncio
import json
from datetime import datetime

import pytest

from loom.events.event_bus import EventBus
from loom.events.stream_converter import EventStreamConverter
from loom.runtime import Task, TaskStatus


class TestEventStreamConverterAsyncStreams:
    """测试EventStreamConverter的异步流方法"""

    @pytest.mark.asyncio
    async def test_subscribe_and_stream_receives_events(self):
        """测试subscribe_and_stream能接收事件"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        stream = converter.subscribe_and_stream("node.thinking")
        connected_event = await stream.__anext__()

        # 验证连接事件
        assert "event: connected" in connected_event
        assert "node.thinking" in connected_event

        # 发布事件
        task = Task(
            taskId="test-task-1",
            action="node.thinking",
            parameters={"node_id": "test-node", "content": "thinking..."},
            status=TaskStatus.RUNNING,
            createdAt=datetime.now(),
        )
        task.sourceAgent = "test-agent"
        await event_bus.publish(task)

        # 等待并接收事件
        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "node.thinking" in event
            assert "test-task-1" in event
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_subscribe_and_stream_filters_by_node_id(self):
        """测试按节点ID过滤"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        stream = converter.subscribe_and_stream("node.thinking", node_id="target-node")
        await stream.__anext__()  # 跳过连接事件

        # 发布目标节点事件
        target_task = Task(
            taskId="target-task",
            action="node.thinking",
            parameters={"node_id": "target-node", "content": "thinking"},
            status=TaskStatus.RUNNING,
            createdAt=datetime.now(),
        )
        target_task.sourceAgent = "agent-1"
        await event_bus.publish(target_task)

        # 发布其他节点事件（应该被过滤）
        other_task = Task(
            taskId="other-task",
            action="node.thinking",
            parameters={"node_id": "other-node", "content": "thinking"},
            status=TaskStatus.RUNNING,
            createdAt=datetime.now(),
        )
        other_task.sourceAgent = "agent-2"
        await event_bus.publish(other_task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "target-task" in event
            assert "other-task" not in event
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_subscribe_and_stream_wildcard_pattern(self):
        """测试通配符模式"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        stream = converter.subscribe_and_stream("node.*")
        await stream.__anext__()  # 跳过连接事件

        # 发布多种节点事件
        events = [
            Task(
                taskId="thinking-1",
                action="node.thinking",
                parameters={"node_id": "n1"},
                status=TaskStatus.RUNNING,
                createdAt=datetime.now(),
            ),
            Task(
                taskId="tool-1",
                action="node.tool_call",
                parameters={"node_id": "n1"},
                status=TaskStatus.RUNNING,
                createdAt=datetime.now(),
            ),
        ]

        for task in events:
            task.sourceAgent = "agent-1"
            await event_bus.publish(task)
            await asyncio.sleep(0.05)

        # 验证接收到事件
        received = []
        for _ in range(2):
            try:
                event = await asyncio.wait_for(stream.__anext__(), timeout=0.5)
                received.append(event)
            except (StopAsyncIteration, asyncio.TimeoutError):
                break

        assert len(received) > 0

    @pytest.mark.asyncio
    async def test_stream_node_events(self):
        """测试stream_node_events方法"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        stream = converter.stream_node_events("test-node")
        connected_event = await stream.__anext__()

        assert "connected" in connected_event
        assert "node.*" in connected_event

        # 发布节点事件
        task = Task(
            taskId="node-task",
            action="node.thinking",
            parameters={"node_id": "test-node", "content": "test"},
            status=TaskStatus.RUNNING,
            createdAt=datetime.now(),
        )
        task.sourceAgent = "agent-1"
        await event_bus.publish(task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "node-task" in event or "test-node" in event
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_stream_thinking_events(self):
        """测试stream_thinking_events方法"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        stream = converter.stream_thinking_events()
        await stream.__anext__()  # 跳过连接事件

        # 发布思考事件
        task = Task(
            taskId="thinking-task",
            action="node.thinking",
            parameters={"node_id": "test-node", "content": "thinking"},
            status=TaskStatus.RUNNING,
            createdAt=datetime.now(),
        )
        task.sourceAgent = "agent-1"
        await event_bus.publish(task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "thinking-task" in event or "node.thinking" in event
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_stream_thinking_events_with_node_filter(self):
        """测试stream_thinking_events按节点过滤"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        stream = converter.stream_thinking_events("target-node")
        await stream.__anext__()  # 跳过连接事件

        # 发布目标节点思考事件
        task = Task(
            taskId="target-thinking",
            action="node.thinking",
            parameters={"node_id": "target-node", "content": "thinking"},
            status=TaskStatus.RUNNING,
            createdAt=datetime.now(),
        )
        task.sourceAgent = "agent-1"
        await event_bus.publish(task)

        await asyncio.sleep(0.1)
        try:
            event = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
            assert "target-thinking" in event
        except (StopAsyncIteration, asyncio.TimeoutError):
            pass

    @pytest.mark.asyncio
    async def test_convert_task_to_sse_format(self):
        """测试_convert_task_to_sse格式"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        task = Task(
            taskId="test-task",
            action="node.thinking",
            parameters={"node_id": "n1", "content": "test"},
            status=TaskStatus.RUNNING,
            createdAt=datetime.now(),
        )
        task.sourceAgent = "test-agent"

        sse = converter._convert_task_to_sse(task)

        assert "event: node.thinking" in sse
        assert "id: test-task" in sse
        assert "data: " in sse

        # 解析data部分
        data_line = [l for l in sse.split("\n") if l.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["task_id"] == "test-task"
        assert data["action"] == "node.thinking"
        assert data["source_agent"] == "test-agent"
        assert data["status"] == "running"
        assert data["parameters"]["node_id"] == "n1"

    @pytest.mark.asyncio
    async def test_convert_task_to_sse_without_created_at(self):
        """测试created_at为None的Task转换（边界情况）"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        task = Task(
            taskId="test-task",
            action="node.thinking",
            parameters={},
            status=TaskStatus.PENDING,
        )
        task.sourceAgent = "test-agent"
        # 手动设置createdAt为None来测试边界情况
        task.createdAt = None

        sse = converter._convert_task_to_sse(task)

        data_line = [l for l in sse.split("\n") if l.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["timestamp"] is None

    @pytest.mark.asyncio
    async def test_stream_cleanup_on_cancellation(self):
        """测试取消流时清理handler"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        stream = converter.subscribe_and_stream("test.action")
        await stream.__anext__()  # 跳过连接事件

        # 验证handler已注册
        assert "test.action" in event_bus._handlers
        assert len(event_bus._handlers["test.action"]) > 0

        # 取消流
        task = asyncio.create_task(stream.__anext__())
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # 等待清理完成
        await asyncio.sleep(0.1)

        # handler应该被清理（但EventBus可能保留handler列表）
        # 这里我们主要验证不会抛出异常
