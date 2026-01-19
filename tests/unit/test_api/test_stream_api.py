"""
Stream API Unit Tests

测试流式观测API功能
"""

from unittest.mock import Mock, patch

import pytest

from loom.api.stream_api import StreamAPI
from loom.events.event_bus import EventBus


class TestStreamAPIInit:
    """测试StreamAPI初始化"""

    def test_stream_api_init(self):
        """测试基本初始化"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.EventStreamConverter") as mock_converter:
            api = StreamAPI(event_bus)

            assert api.event_bus == event_bus
            mock_converter.assert_called_once_with(event_bus)


class TestStreamNodeEvents:
    """测试订阅节点事件"""

    @pytest.mark.asyncio
    async def test_stream_node_events(self):
        """测试订阅特定节点的事件"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.EventStreamConverter") as mock_converter_class:
            mock_converter = Mock()
            mock_converter_class.return_value = mock_converter

            # Mock异步生成器
            async def mock_stream():
                yield "event: node.start\ndata: {}\n\n"
                yield "event: node.complete\ndata: {}\n\n"

            mock_converter.stream_node_events = Mock(return_value=mock_stream())

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_node_events("test-node"):
                events.append(event)

            assert len(events) == 2
            mock_converter.stream_node_events.assert_called_once_with("test-node")


class TestStreamThinkingEvents:
    """测试订阅思考过程事件"""

    @pytest.mark.asyncio
    async def test_stream_thinking_events_with_node_id(self):
        """测试订阅特定节点的思考事件"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.EventStreamConverter") as mock_converter_class:
            mock_converter = Mock()
            mock_converter_class.return_value = mock_converter

            async def mock_stream():
                yield "event: node.thinking\ndata: {}\n\n"

            mock_converter.stream_thinking_events = Mock(return_value=mock_stream())

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_thinking_events("test-node"):
                events.append(event)

            assert len(events) == 1
            mock_converter.stream_thinking_events.assert_called_once_with("test-node")

    @pytest.mark.asyncio
    async def test_stream_thinking_events_without_node_id(self):
        """测试订阅所有思考事件"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.EventStreamConverter") as mock_converter_class:
            mock_converter = Mock()
            mock_converter_class.return_value = mock_converter

            async def mock_stream():
                yield "event: node.thinking\ndata: {}\n\n"

            mock_converter.stream_thinking_events = Mock(return_value=mock_stream())

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_thinking_events(None):
                events.append(event)

            assert len(events) == 1
            mock_converter.stream_thinking_events.assert_called_once_with(None)


class TestStreamAllEvents:
    """测试订阅所有事件"""

    @pytest.mark.asyncio
    async def test_stream_all_events_default_pattern(self):
        """测试订阅所有事件（默认模式）"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.EventStreamConverter") as mock_converter_class:
            mock_converter = Mock()
            mock_converter_class.return_value = mock_converter

            async def mock_stream():
                yield "event: node.start\ndata: {}\n\n"
                yield "event: node.complete\ndata: {}\n\n"

            mock_converter.subscribe_and_stream = Mock(return_value=mock_stream())

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_all_events():
                events.append(event)

            assert len(events) == 2
            mock_converter.subscribe_and_stream.assert_called_once_with("node.*")

    @pytest.mark.asyncio
    async def test_stream_all_events_custom_pattern(self):
        """测试订阅所有事件（自定义模式）"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.EventStreamConverter") as mock_converter_class:
            mock_converter = Mock()
            mock_converter_class.return_value = mock_converter

            async def mock_stream():
                yield "event: agent.start\ndata: {}\n\n"

            mock_converter.subscribe_and_stream = Mock(return_value=mock_stream())

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_all_events("agent.*"):
                events.append(event)

            assert len(events) == 1
            mock_converter.subscribe_and_stream.assert_called_once_with("agent.*")
