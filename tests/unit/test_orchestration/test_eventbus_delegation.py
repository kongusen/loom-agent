"""
EventBus Delegation Handler Unit Tests

测试 EventBus 委派处理器的功能
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from loom.events.queryable_event_bus import QueryableEventBus
from loom.orchestration.eventbus_delegation import EventBusDelegationHandler
from loom.protocol import Task, TaskStatus


class TestEventBusDelegationHandler:
    """测试 EventBusDelegationHandler"""

    @pytest.fixture
    def event_bus(self):
        """创建 QueryableEventBus 实例"""
        return QueryableEventBus()

    @pytest.fixture
    def handler(self, event_bus):
        """创建 EventBusDelegationHandler 实例"""
        return EventBusDelegationHandler(event_bus, timeout=5.0)

    @pytest.mark.asyncio
    async def test_init(self, event_bus):
        """测试初始化"""
        handler = EventBusDelegationHandler(event_bus, timeout=10.0)
        assert handler.event_bus == event_bus
        assert handler.timeout == 10.0
        assert handler._pending_requests == {}

    @pytest.mark.asyncio
    async def test_delegate_task_success(self, handler, event_bus):
        """测试成功委派任务"""
        source_agent_id = "agent1"
        target_agent_id = "agent2"
        subtask = "处理子任务"
        parent_task_id = "parent-task-123"

        request_id = f"{parent_task_id}:delegated:{target_agent_id}"

        # 模拟响应事件 - 直接调用 handle_response
        async def send_response():
            await asyncio.sleep(0.1)
            response_event = {
                "request_id": request_id,
                "result": "任务完成",
            }
            await handler.handle_response(response_event)

        # 启动响应任务
        asyncio.create_task(send_response())

        # 执行委派
        result = await handler.delegate_task(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            subtask=subtask,
            parent_task_id=parent_task_id,
        )

        assert result == "任务完成"
        assert len(handler._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_delegate_task_timeout(self, handler):
        """测试委派任务超时"""
        source_agent_id = "agent1"
        target_agent_id = "agent2"
        subtask = "处理子任务"
        parent_task_id = "parent-task-123"

        # 使用很短的超时时间
        handler.timeout = 0.1

        # 执行委派（不会收到响应）
        result = await handler.delegate_task(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            subtask=subtask,
            parent_task_id=parent_task_id,
        )

        assert "timeout" in result.lower()
        assert target_agent_id in result
        assert len(handler._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_handle_response_success(self, handler):
        """测试处理响应成功"""
        request_id = "test-request-123"
        future = asyncio.Future()
        handler._pending_requests[request_id] = future

        # 处理响应
        response_event = {
            "request_id": request_id,
            "result": "响应结果",
        }

        await handler.handle_response(response_event)

        # 验证 Future 已完成
        assert future.done()
        assert await future == "响应结果"
        assert request_id not in handler._pending_requests

    @pytest.mark.asyncio
    async def test_handle_response_no_request_id(self, handler):
        """测试处理响应但没有 request_id"""
        # 处理没有 request_id 的响应
        response_event = {"result": "响应结果"}

        await handler.handle_response(response_event)

        # 应该没有影响
        assert len(handler._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_handle_response_unknown_request(self, handler):
        """测试处理未知请求的响应"""
        response_event = {
            "request_id": "unknown-request",
            "result": "响应结果",
        }

        await handler.handle_response(response_event)

        # 应该没有影响
        assert len(handler._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_delegate_task_publishes_event(self, handler, event_bus):
        """测试委派任务会发布事件"""
        source_agent_id = "agent1"
        target_agent_id = "agent2"
        subtask = "处理子任务"
        parent_task_id = "parent-task-123"

        # 注册处理器来捕获事件
        captured_tasks = []

        async def capture_handler(task: Task) -> Task:
            captured_tasks.append(task)
            return task

        event_bus.register_handler("node.delegation_request", capture_handler)

        # 执行委派（不等待响应）
        request_id = f"{parent_task_id}:delegated:{target_agent_id}"

        # 启动委派任务（不等待完成）
        delegate_task = asyncio.create_task(
            handler.delegate_task(
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
                subtask=subtask,
                parent_task_id=parent_task_id,
            )
        )

        # 等待一小段时间让事件发布
        await asyncio.sleep(0.1)

        # 验证事件已发布
        assert len(captured_tasks) > 0
        published_task = captured_tasks[0]
        assert published_task.action == "node.delegation_request"
        assert published_task.parameters["source_agent"] == source_agent_id
        assert published_task.parameters["target_agent"] == target_agent_id
        assert published_task.parameters["subtask"] == subtask
        assert published_task.parameters["parent_task_id"] == parent_task_id

        # 取消任务以避免超时
        delegate_task.cancel()
        try:
            await delegate_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_delegate_task_generic_exception(self, handler, monkeypatch):
        """测试委派任务通用异常处理"""
        import unittest.mock

        source_agent_id = "agent1"
        target_agent_id = "agent2"
        subtask = "处理子任务"
        parent_task_id = "parent-task-123"

        # Mock asyncio.wait_for to raise a non-TimeoutError exception
        async def mock_wait_for(fut, timeout):
            raise RuntimeError("Simulated error")

        monkeypatch.setattr("asyncio.wait_for", mock_wait_for)

        # 执行委派（应该触发通用异常处理）
        result = await handler.delegate_task(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            subtask=subtask,
            parent_task_id=parent_task_id,
        )

        # 应该返回错误信息
        assert "delegation error" in result.lower()
        assert len(handler._pending_requests) == 0
