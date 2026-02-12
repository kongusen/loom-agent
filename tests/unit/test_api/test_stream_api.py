"""
Stream API Unit Tests

测试流式观测API功能
"""

from unittest.mock import Mock, patch

import pytest

from loom.api.stream_api import FractalStreamAPI, OutputStrategy, StreamAPI
from loom.events.event_bus import EventBus


class TestStreamAPIInit:
    """测试StreamAPI初始化"""

    def test_stream_api_init(self):
        """测试基本初始化"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.FractalStreamAPI") as mock_fractal_api:
            api = StreamAPI(event_bus)

            assert api.event_bus == event_bus
            mock_fractal_api.assert_called_once_with(event_bus)

    def test_stream_api_has_fractal_api(self):
        """测试StreamAPI包含FractalStreamAPI实例"""
        event_bus = EventBus()
        api = StreamAPI(event_bus)

        assert hasattr(api, "_fractal_api")
        assert isinstance(api._fractal_api, FractalStreamAPI)


class TestFractalStreamAPIInit:
    """测试FractalStreamAPI初始化"""

    def test_fractal_stream_api_init(self):
        """测试FractalStreamAPI基本初始化"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        assert api.event_bus == event_bus
        assert api._node_registry == {}

    def test_register_node(self):
        """测试节点注册"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        api.register_node("child-1", "root")
        api.register_node("child-2", "root")
        api.register_node("grandchild-1", "child-1")

        assert api._node_registry["child-1"] == "root"
        assert api._node_registry["child-2"] == "root"
        assert api._node_registry["grandchild-1"] == "child-1"

    def test_get_node_path(self):
        """测试获取节点路径"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        api.register_node("child-1", "root")
        api.register_node("grandchild-1", "child-1")

        assert api.get_node_path("grandchild-1") == "root/child-1/grandchild-1"
        assert api.get_node_path("child-1") == "root/child-1"
        assert api.get_node_path("unknown") == "unknown"

    def test_get_node_depth(self):
        """测试获取节点深度"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        api.register_node("child-1", "root")
        api.register_node("grandchild-1", "child-1")

        assert api.get_node_depth("root") == 0
        assert api.get_node_depth("child-1") == 1
        assert api.get_node_depth("grandchild-1") == 2


class TestStreamNodeEvents:
    """测试订阅节点事件"""

    @pytest.mark.asyncio
    async def test_stream_node_events(self):
        """测试订阅特定节点的事件"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.FractalStreamAPI") as mock_fractal_api_class:
            mock_fractal_api = Mock()
            mock_fractal_api_class.return_value = mock_fractal_api

            # Mock异步生成器
            async def mock_stream(node_id, include_children=True):
                yield "event: connected\ndata: {}\n\n"
                yield "event: node.thinking\ndata: {}\n\n"

            mock_fractal_api.stream_node_events = mock_stream

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_node_events("test-node"):
                events.append(event)

            assert len(events) == 2


class TestStreamThinkingEvents:
    """测试订阅思考过程事件"""

    @pytest.mark.asyncio
    async def test_stream_thinking_events_with_node_id(self):
        """测试订阅特定节点的思考事件"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.FractalStreamAPI") as mock_fractal_api_class:
            mock_fractal_api = Mock()
            mock_fractal_api_class.return_value = mock_fractal_api

            async def mock_stream(node_id=None):
                yield "event: connected\ndata: {}\n\n"
                yield "event: node.thinking\ndata: {}\n\n"

            mock_fractal_api.stream_thinking_events = mock_stream

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_thinking_events("test-node"):
                events.append(event)

            assert len(events) == 2

    @pytest.mark.asyncio
    async def test_stream_thinking_events_without_node_id(self):
        """测试订阅所有思考事件"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.FractalStreamAPI") as mock_fractal_api_class:
            mock_fractal_api = Mock()
            mock_fractal_api_class.return_value = mock_fractal_api

            async def mock_stream(node_id=None):
                yield "event: connected\ndata: {}\n\n"
                yield "event: node.thinking\ndata: {}\n\n"

            mock_fractal_api.stream_thinking_events = mock_stream

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_thinking_events(None):
                events.append(event)

            assert len(events) == 2


class TestStreamAllEvents:
    """测试订阅所有事件"""

    @pytest.mark.asyncio
    async def test_stream_all_events_default_pattern(self):
        """测试订阅所有事件（默认模式）"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.FractalStreamAPI") as mock_fractal_api_class:
            mock_fractal_api = Mock()
            mock_fractal_api_class.return_value = mock_fractal_api

            async def mock_stream(strategy=OutputStrategy.REALTIME):
                yield "event: connected\ndata: {}\n\n"
                yield "event: node.thinking\ndata: {}\n\n"
                yield "event: node.tool_call\ndata: {}\n\n"

            mock_fractal_api.stream_all_events = mock_stream

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_all_events():
                events.append(event)

            assert len(events) == 3

    @pytest.mark.asyncio
    async def test_stream_all_events_custom_pattern(self):
        """测试订阅所有事件（自定义模式）"""
        event_bus = EventBus()

        with patch("loom.api.stream_api.FractalStreamAPI") as mock_fractal_api_class:
            mock_fractal_api = Mock()
            mock_fractal_api_class.return_value = mock_fractal_api

            async def mock_stream(strategy=OutputStrategy.REALTIME):
                yield "event: connected\ndata: {}\n\n"
                yield "event: agent.start\ndata: {}\n\n"

            mock_fractal_api.stream_all_events = mock_stream

            api = StreamAPI(event_bus)
            events = []
            async for event in api.stream_all_events("agent.*"):
                events.append(event)

            assert len(events) == 2


class TestOutputStrategy:
    """测试输出策略枚举"""

    def test_output_strategy_values(self):
        """测试OutputStrategy枚举值"""
        assert OutputStrategy.REALTIME.value == "realtime"
        assert OutputStrategy.BY_NODE.value == "by_node"
        assert OutputStrategy.TREE.value == "tree"
