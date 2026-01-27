"""
Task Context Unit Tests

测试基于 Task 的上下文管理功能
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.events.queryable_event_bus import QueryableEventBus
from loom.memory.core import LoomMemory
from loom.memory.task_context import (
    EventBusContextSource,
    MemoryContextSource,
    MessageConverter,
    TaskContextManager,
)
from loom.memory.tokenizer import EstimateCounter
from loom.protocol import Task, TaskStatus


class TestMessageConverter:
    """测试 MessageConverter"""

    def test_convert_thinking_task(self):
        """测试转换思考任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"content": "我在思考问题"},
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert message["content"] == "我在思考问题"

    def test_convert_thinking_task_empty_content(self):
        """测试转换空内容的思考任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={},
        )

        message = converter.convert_task_to_message(task)

        assert message is None

    def test_convert_tool_call_task(self):
        """测试转换工具调用任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.tool_call",
            parameters={"tool_name": "test_tool", "tool_args": {"arg1": "value1"}},
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert "test_tool" in message["content"]

    def test_convert_execute_task(self):
        """测试转换执行任务"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="execute",
            parameters={"content": "执行任务"},
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "user"
        assert message["content"] == "执行任务"

    def test_convert_unknown_action(self):
        """测试转换未知动作"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="unknown_action",
            parameters={},
        )

        message = converter.convert_task_to_message(task)

        assert message is None

    def test_convert_tasks_to_messages(self):
        """测试批量转换任务"""
        converter = MessageConverter()

        tasks = [
            Task(
                task_id="task-1",
                action="node.thinking",
                parameters={"content": "思考1"},
            ),
            Task(
                task_id="task-2",
                action="execute",
                parameters={"content": "执行任务"},
            ),
            Task(
                task_id="task-3",
                action="unknown_action",
                parameters={},
            ),
        ]

        messages = converter.convert_tasks_to_messages(tasks)

        assert len(messages) == 2
        assert messages[0]["role"] == "assistant"
        assert messages[1]["role"] == "user"


class TestMemoryContextSource:
    """测试 MemoryContextSource"""

    @pytest.mark.asyncio
    async def test_get_context(self):
        """测试获取上下文"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些任务到记忆
        task1 = Task(
            task_id="task-1",
            action="test_action",
            parameters={"content": "任务1"},
        )
        task1.status = TaskStatus.COMPLETED
        memory.add_task(task1)

        task2 = Task(
            task_id="task-2",
            action="test_action",
            parameters={"content": "任务2"},
        )
        task2.status = TaskStatus.COMPLETED
        memory.add_task(task2)

        source = MemoryContextSource(memory)
        current_task = Task(task_id="current", action="test")

        context = await source.get_context(current_task, max_items=10)

        assert len(context) > 0
        assert any(t.task_id == "task-1" or t.task_id == "task-2" for t in context)

    @pytest.mark.asyncio
    async def test_get_context_respects_max_items(self):
        """测试遵守最大数量限制"""
        memory = LoomMemory(node_id="test-node")

        # 添加多个任务
        for i in range(10):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"content": f"任务{i}"},
            )
            task.status = TaskStatus.COMPLETED
            memory.add_task(task)

        source = MemoryContextSource(memory)
        current_task = Task(task_id="current", action="test")

        context = await source.get_context(current_task, max_items=5)

        assert len(context) <= 5


class TestEventBusContextSource:
    """测试 EventBusContextSource"""

    @pytest.mark.asyncio
    async def test_get_context(self):
        """测试获取上下文"""
        event_bus = QueryableEventBus()

        # 添加一些事件
        task1 = Task(
            task_id="task-1",
            action="node.thinking",
            parameters={"node_id": "node-1", "content": "思考1", "parent_task_id": "parent-1"},
            parent_task_id="parent-1",
        )
        await event_bus.publish(task1)

        task2 = Task(
            task_id="task-2",
            action="node.thinking",
            parameters={"node_id": "node-1", "content": "思考2", "parent_task_id": "parent-1"},
            parent_task_id="parent-1",
        )
        await event_bus.publish(task2)

        source = EventBusContextSource(event_bus)
        current_task = Task(
            task_id="parent-1",
            action="test",
            parameters={"node_id": "node-1"},
        )

        context = await source.get_context(current_task, max_items=10)

        assert len(context) > 0

    @pytest.mark.asyncio
    async def test_get_context_without_node_id(self):
        """测试没有 node_id 时获取上下文"""
        event_bus = QueryableEventBus()

        source = EventBusContextSource(event_bus)
        current_task = Task(task_id="task-1", action="test")

        context = await source.get_context(current_task, max_items=10)

        # 应该只返回任务相关的事件
        assert isinstance(context, list)


class TestTaskContextManager:
    """测试 TaskContextManager"""

    @pytest.fixture
    def token_counter(self):
        """提供 token 计数器"""
        return EstimateCounter()

    @pytest.fixture
    def memory(self):
        """提供内存实例"""
        return LoomMemory(node_id="test-node")

    @pytest.fixture
    def context_manager(self, token_counter, memory):
        """提供上下文管理器"""
        sources = [MemoryContextSource(memory)]
        return TaskContextManager(
            token_counter=token_counter,
            sources=sources,
            max_tokens=1000,
            system_prompt="Test system prompt",
        )

    def test_init(self, token_counter, memory):
        """测试初始化"""
        sources = [MemoryContextSource(memory)]
        manager = TaskContextManager(
            token_counter=token_counter,
            sources=sources,
            max_tokens=2000,
            system_prompt="Test",
        )

        assert manager.token_counter == token_counter
        assert len(manager.sources) == 1
        assert manager.max_tokens == 2000
        assert manager.system_prompt == "Test"
        assert isinstance(manager.converter, MessageConverter)

    @pytest.mark.asyncio
    async def test_build_context_basic(self, context_manager, memory):
        """测试基本上下文构建"""
        # 添加任务到记忆
        task = Task(
            task_id="task-1",
            action="execute",
            parameters={"content": "测试任务"},
        )
        task.status = TaskStatus.COMPLETED
        memory.add_task(task)

        current_task = Task(
            task_id="current",
            action="execute",
            parameters={"content": "当前任务"},
        )

        messages = await context_manager.build_context(current_task)

        assert len(messages) > 0
        assert any(m.get("role") == "system" for m in messages)

    @pytest.mark.asyncio
    async def test_build_context_with_knowledge_base(self, token_counter, memory):
        """测试带知识库的上下文构建"""
        mock_kb = Mock()
        mock_kb.query = AsyncMock(
            return_value=[
                Mock(content="知识1", source="source1"),
                Mock(content="知识2", source="source2"),
            ]
        )

        sources = [MemoryContextSource(memory)]
        manager = TaskContextManager(
            token_counter=token_counter,
            sources=sources,
            max_tokens=1000,
            knowledge_base=mock_kb,
        )

        current_task = Task(task_id="current", action="test_action")

        messages = await manager.build_context(current_task)

        mock_kb.query.assert_called_once()
        assert any("📚 Knowledge" in str(m.get("content", "")) for m in messages)

    @pytest.mark.asyncio
    async def test_build_context_without_system_prompt(self, token_counter, memory):
        """测试没有系统提示词的上下文构建"""
        sources = [MemoryContextSource(memory)]
        manager = TaskContextManager(
            token_counter=token_counter,
            sources=sources,
            max_tokens=1000,
            system_prompt="",
        )

        current_task = Task(
            task_id="current",
            action="execute",
            parameters={"content": "当前任务"},
        )

        messages = await manager.build_context(current_task)

        # 不应该有系统消息
        assert not any(m.get("role") == "system" for m in messages) or len(messages) == 0

    def test_fit_to_token_limit_within_limit(self, context_manager):
        """测试 token 限制内的情况"""
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Short message"},
        ]

        result = context_manager._fit_to_token_limit(messages)

        assert len(result) == 2

    def test_fit_to_token_limit_exceeds_limit(self, token_counter, memory):
        """测试超过 token 限制的情况"""
        sources = [MemoryContextSource(memory)]
        manager = TaskContextManager(
            token_counter=token_counter,
            sources=sources,
            max_tokens=10,  # 很小的限制
            system_prompt="System prompt",
        )

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "This is a very long message that exceeds the token limit"},
            {"role": "user", "content": "Another long message"},
        ]

        result = manager._fit_to_token_limit(messages)

        # 应该保留系统消息和部分其他消息
        assert len(result) <= len(messages)
        assert result[0]["role"] == "system"

    def test_fit_to_token_limit_no_system_message(self, token_counter, memory):
        """测试没有系统消息的情况"""
        sources = [MemoryContextSource(memory)]
        manager = TaskContextManager(
            token_counter=token_counter,
            sources=sources,
            max_tokens=10,
            system_prompt="",
        )

        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "user", "content": "Message 2"},
        ]

        result = manager._fit_to_token_limit(messages)

        assert len(result) <= len(messages)

    def test_fit_to_token_limit_system_too_large(self, token_counter, memory):
        """测试系统消息太大无法容纳的情况"""
        sources = [MemoryContextSource(memory)]
        manager = TaskContextManager(
            token_counter=token_counter,
            sources=sources,
            max_tokens=5,  # 非常小的限制
            system_prompt="This is a very long system prompt that exceeds the token limit",
        )

        messages = [
            {
                "role": "system",
                "content": "This is a very long system prompt that exceeds the token limit",
            },
        ]

        result = manager._fit_to_token_limit(messages)

        # 应该只返回系统消息
        assert len(result) == 1
        assert result[0]["role"] == "system"
