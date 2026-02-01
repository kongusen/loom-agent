"""
Task Context Unit Tests

测试基于 Task 的上下文管理功能
"""

import pytest

from loom.memory.core import LoomMemory
from loom.memory.task_context import (
    MemoryContextSource,
    MessageConverter,
)
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

    def test_convert_node_message_task(self):
        """测试转换节点消息"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.message",
            parameters={"content": "直接消息"},
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert "直接消息" in message["content"]

    def test_convert_delegation_request_task(self):
        """测试转换委派请求"""
        converter = MessageConverter()

        task = Task(
            task_id="task-1",
            action="node.delegation_request",
            parameters={"subtask": "处理子任务"},
            source_agent="agent-1",
        )

        message = converter.convert_task_to_message(task)

        assert message is not None
        assert message["role"] == "assistant"
        assert "处理子任务" in message["content"]

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
