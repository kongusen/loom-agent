"""
Tests for loom/api/stream_api.py - FractalStreamAPI, FractalEvent, OutputStrategy
"""


from loom.api.stream_api import (
    FractalEvent,
    FractalStreamAPI,
    OutputStrategy,
    StreamAPI,
)
from loom.events import EventBus
from loom.runtime import Task, TaskStatus

# ==================== OutputStrategy ====================


class TestOutputStrategy:
    def test_values(self):
        assert OutputStrategy.REALTIME.value == "realtime"
        assert OutputStrategy.BY_NODE.value == "by_node"
        assert OutputStrategy.TREE.value == "tree"


# ==================== FractalEvent ====================


class TestFractalEvent:
    def test_to_dict(self):
        task = Task(
            taskId="t1",
            action="node.thinking",
            parameters={"node_id": "worker-1", "content": "thinking..."},
            status=TaskStatus.RUNNING,
        )
        event = FractalEvent(
            task=task,
            node_path="root/worker-1",
            depth=1,
            parent_node_id="root",
            metadata={"extra": "data"},
        )
        d = event.to_dict()
        assert d["task_id"] == "t1"
        assert d["action"] == "node.thinking"
        assert d["node_path"] == "root/worker-1"
        assert d["depth"] == 1
        assert d["parent_node_id"] == "root"
        assert d["status"] == "running"

    def test_to_dict_no_node_id(self):
        task = Task(taskId="t1", action="test", parameters={})
        event = FractalEvent(task=task, node_path="root", depth=0, parent_node_id=None)
        d = event.to_dict()
        assert d["node_id"] == ""


# ==================== FractalStreamAPI ====================


class TestFractalStreamAPI:
    def test_init(self):
        bus = EventBus()
        api = FractalStreamAPI(bus)
        assert api.event_bus is bus
        assert api._node_registry == {}

    def test_register_node(self):
        api = FractalStreamAPI(EventBus())
        api.register_node("worker-1", "root")
        assert api._node_registry["worker-1"] == "root"

    def test_register_node_no_parent(self):
        api = FractalStreamAPI(EventBus())
        api.register_node("root")
        assert api._node_registry["root"] == ""

    def test_resolve_node_info_root(self):
        api = FractalStreamAPI(EventBus())
        api.register_node("root")
        path, depth = api.resolve_node_info("root")
        assert path == "root"
        assert depth == 0

    def test_resolve_node_info_nested(self):
        api = FractalStreamAPI(EventBus())
        api.register_node("root")
        api.register_node("worker-1", "root")
        api.register_node("subtask-1", "worker-1")
        path, depth = api.resolve_node_info("subtask-1")
        assert path == "root/worker-1/subtask-1"
        assert depth == 2

    def test_resolve_node_info_unregistered(self):
        api = FractalStreamAPI(EventBus())
        path, depth = api.resolve_node_info("unknown")
        assert path == "unknown"
        assert depth == 0

    def test_format_connected_event(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_connected_event(OutputStrategy.REALTIME)
        assert "connected" in result
        assert "realtime" in result

    def test_format_connected_event_with_extra(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_connected_event(
            OutputStrategy.BY_NODE, {"node_id": "w1"}
        )
        assert "w1" in result

    def test_format_disconnected_event(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_disconnected_event()
        assert "disconnected" in result

    def test_format_heartbeat(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_heartbeat()
        assert "heartbeat" in result

    def test_format_fractal_event_realtime(self):
        api = FractalStreamAPI(EventBus())
        api.register_node("root")
        api.register_node("w1", "root")
        task = Task(
            taskId="t1",
            action="node.thinking",
            parameters={"node_id": "w1", "content": "thinking about stuff"},
        )
        result = api._format_fractal_event(task, OutputStrategy.REALTIME)
        assert "node.thinking" in result
        assert "w1" in result

    def test_format_fractal_event_tree(self):
        api = FractalStreamAPI(EventBus())
        api.register_node("root")
        api.register_node("w1", "root")
        task = Task(
            taskId="t1",
            action="node.thinking",
            parameters={"node_id": "w1", "content": "thinking about stuff"},
        )
        result = api._format_fractal_event(task, OutputStrategy.TREE)
        assert "display" in result  # tree mode adds display field


# ==================== StreamAPI ====================


class TestStreamAPI:
    def test_is_alias(self):
        assert StreamAPI is FractalStreamAPI

    def test_init(self):
        bus = EventBus()
        api = StreamAPI(bus)
        assert api.event_bus is bus
