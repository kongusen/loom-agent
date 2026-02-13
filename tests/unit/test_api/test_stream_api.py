"""
Stream API Unit Tests

测试流式观测API功能
"""

import pytest

from loom.api.stream_api import FractalStreamAPI, OutputStrategy, StreamAPI
from loom.events.event_bus import EventBus


class TestStreamAPIAlias:
    """测试 StreamAPI 是 FractalStreamAPI 的别名"""

    def test_stream_api_is_fractal_stream_api(self):
        """StreamAPI 应该是 FractalStreamAPI 的别名"""
        assert StreamAPI is FractalStreamAPI

    def test_stream_api_init(self):
        """测试通过 StreamAPI 别名初始化"""
        event_bus = EventBus()
        api = StreamAPI(event_bus)

        assert api.event_bus == event_bus
        assert api._node_registry == {}


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

    def test_resolve_node_info_path(self):
        """测试 resolve_node_info 返回正确路径"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        api.register_node("child-1", "root")
        api.register_node("grandchild-1", "child-1")

        path, _ = api.resolve_node_info("grandchild-1")
        assert path == "root/child-1/grandchild-1"

        path, _ = api.resolve_node_info("child-1")
        assert path == "root/child-1"

        path, _ = api.resolve_node_info("unknown")
        assert path == "unknown"

    def test_resolve_node_info_depth(self):
        """测试 resolve_node_info 返回正确深度"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        api.register_node("child-1", "root")
        api.register_node("grandchild-1", "child-1")

        _, depth = api.resolve_node_info("root")
        assert depth == 0

        _, depth = api.resolve_node_info("child-1")
        assert depth == 1

        _, depth = api.resolve_node_info("grandchild-1")
        assert depth == 2

    def test_resolve_node_info_cycle_guard(self):
        """测试环路保护"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        # 制造环路: a -> b -> c -> a
        api._node_registry["a"] = "b"
        api._node_registry["b"] = "c"
        api._node_registry["c"] = "a"

        # 不应死循环
        path, depth = api.resolve_node_info("a")
        assert isinstance(path, str)
        assert isinstance(depth, int)


class TestStreamNodeEvents:
    """测试订阅节点事件"""

    @pytest.mark.asyncio
    async def test_stream_node_events(self):
        """测试订阅特定节点的事件"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        # stream_node_events 是异步生成器，直接测试其存在性
        assert hasattr(api, "stream_node_events")
        assert callable(api.stream_node_events)


class TestStreamThinkingEvents:
    """测试订阅思考过程事件"""

    @pytest.mark.asyncio
    async def test_stream_thinking_events(self):
        """测试 stream_thinking_events 方法存在"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        assert hasattr(api, "stream_thinking_events")
        assert callable(api.stream_thinking_events)


class TestStreamAllEvents:
    """测试订阅所有事件"""

    @pytest.mark.asyncio
    async def test_stream_all_events(self):
        """测试 stream_all_events 方法存在"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        assert hasattr(api, "stream_all_events")
        assert callable(api.stream_all_events)


class TestStreamToolEvents:
    """测试订阅工具事件"""

    @pytest.mark.asyncio
    async def test_stream_tool_events(self):
        """测试 stream_tool_events 方法存在"""
        event_bus = EventBus()
        api = FractalStreamAPI(event_bus)

        assert hasattr(api, "stream_tool_events")
        assert callable(api.stream_tool_events)


class TestOutputStrategy:
    """测试输出策略枚举"""

    def test_output_strategy_values(self):
        """测试OutputStrategy枚举值"""
        assert OutputStrategy.REALTIME.value == "realtime"
        assert OutputStrategy.BY_NODE.value == "by_node"
        assert OutputStrategy.TREE.value == "tree"
