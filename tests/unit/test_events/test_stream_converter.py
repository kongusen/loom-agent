"""
Event Stream Converter Unit Tests

测试事件流转换器
"""

from unittest.mock import patch

from loom.events.event_bus import EventBus
from loom.events.stream_converter import EventStreamConverter
from loom.protocol import Task, TaskStatus


class TestEventStreamConverterInit:
    """测试EventStreamConverter初始化"""

    def test_init(self):
        """测试基本初始化"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        assert converter.event_bus == event_bus
        assert converter._subscriptions == {}


class TestConvertTaskToSSE:
    """测试Task转SSE格式"""

    @patch("loom.events.stream_converter.SSEFormatter")
    def test_convert_task_to_sse(self, mock_formatter):
        """测试将Task转换为SSE格式"""
        event_bus = EventBus()
        converter = EventStreamConverter(event_bus)

        mock_formatter.format_sse_message.return_value = "formatted_sse"

        task = Task(
            task_id="task-1",
            action="node.start",
            parameters={"param1": "value1"},
        )
        task.source_agent = "agent-1"
        task.status = TaskStatus.PENDING

        result = converter._convert_task_to_sse(task)

        assert result == "formatted_sse"
        mock_formatter.format_sse_message.assert_called_once()
