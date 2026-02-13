"""
Tests for FractalEvent and FractalStreamAPI formatting methods in loom/api/stream_api.py.

Covers:
- FractalEvent.to_dict() with various Task configurations and metadata
- FractalStreamAPI._format_fractal_event() with REALTIME and TREE strategies
- FractalStreamAPI._format_connected_event() with and without extra data
- FractalStreamAPI._format_disconnected_event()
- FractalStreamAPI._format_heartbeat()
"""

import json

import pytest

from loom.api.stream_api import FractalEvent, FractalStreamAPI, OutputStrategy
from loom.events.event_bus import EventBus
from loom.runtime import Task, TaskStatus

# ==================== FractalEvent.to_dict ====================


class TestFractalEventToDict:
    """Deep verification of FractalEvent.to_dict() output."""

    def _make_task(self, **kwargs):
        defaults = {
            "taskId": "task-100",
            "action": "node.thinking",
            "parameters": {"node_id": "w1", "content": "hello world"},
            "status": TaskStatus.RUNNING,
        }
        defaults.update(kwargs)
        return Task(**defaults)

    def test_all_fields_present(self):
        task = self._make_task()
        event = FractalEvent(
            task=task,
            node_path="root/w1",
            depth=1,
            parent_node_id="root",
        )
        d = event.to_dict()

        assert set(d.keys()) == {
            "task_id",
            "action",
            "node_id",
            "node_path",
            "depth",
            "parent_node_id",
            "parameters",
            "status",
            "metadata",
        }

    def test_values_match_task(self):
        task = self._make_task(
            taskId="abc-123",
            action="node.tool_call",
            parameters={"node_id": "n5", "tool": "search"},
            status=TaskStatus.COMPLETED,
        )
        event = FractalEvent(
            task=task,
            node_path="root/n5",
            depth=1,
            parent_node_id="root",
        )
        d = event.to_dict()

        assert d["task_id"] == "abc-123"
        assert d["action"] == "node.tool_call"
        assert d["node_id"] == "n5"
        assert d["node_path"] == "root/n5"
        assert d["depth"] == 1
        assert d["parent_node_id"] == "root"
        assert d["parameters"] == {"node_id": "n5", "tool": "search"}
        assert d["status"] == "completed"

    def test_missing_node_id_in_parameters(self):
        task = self._make_task(parameters={"content": "no node_id key"})
        event = FractalEvent(task=task, node_path="root", depth=0, parent_node_id=None)
        d = event.to_dict()

        assert d["node_id"] == ""

    def test_parent_node_id_none(self):
        task = self._make_task()
        event = FractalEvent(task=task, node_path="root", depth=0, parent_node_id=None)
        d = event.to_dict()

        assert d["parent_node_id"] is None

    def test_status_serialized_as_string(self):
        for status in TaskStatus:
            task = self._make_task(status=status)
            event = FractalEvent(task=task, node_path="x", depth=0, parent_node_id=None)
            d = event.to_dict()
            assert d["status"] == status.value
            assert isinstance(d["status"], str)

    def test_metadata_default_empty(self):
        task = self._make_task()
        event = FractalEvent(task=task, node_path="x", depth=0, parent_node_id=None)
        assert event.to_dict()["metadata"] == {}

    def test_metadata_preserved(self):
        task = self._make_task()
        meta = {"priority": "high", "tags": ["urgent", "review"], "score": 0.95}
        event = FractalEvent(
            task=task,
            node_path="root/w1",
            depth=1,
            parent_node_id="root",
            metadata=meta,
        )
        d = event.to_dict()

        assert d["metadata"] == meta
        assert d["metadata"]["priority"] == "high"
        assert d["metadata"]["tags"] == ["urgent", "review"]
        assert d["metadata"]["score"] == 0.95

    def test_depth_zero_for_root(self):
        task = self._make_task()
        event = FractalEvent(task=task, node_path="root", depth=0, parent_node_id=None)
        assert event.to_dict()["depth"] == 0

    def test_deep_nesting_depth(self):
        task = self._make_task()
        event = FractalEvent(
            task=task,
            node_path="root/a/b/c/d",
            depth=4,
            parent_node_id="c",
        )
        d = event.to_dict()
        assert d["depth"] == 4
        assert d["node_path"] == "root/a/b/c/d"


# ==================== _format_fractal_event ====================


class TestFormatFractalEvent:
    """Tests for FractalStreamAPI._format_fractal_event with different strategies."""

    def _build_api(self):
        api = FractalStreamAPI(EventBus())
        api.register_node("root")
        api.register_node("w1", "root")
        api.register_node("sub1", "w1")
        return api

    def _make_task(self, node_id="w1", content="thinking hard", **kwargs):
        defaults = {
            "taskId": "evt-001",
            "action": "node.thinking",
            "parameters": {"node_id": node_id, "content": content},
            "status": TaskStatus.RUNNING,
        }
        defaults.update(kwargs)
        return Task(**defaults)

    def test_realtime_returns_valid_sse(self):
        api = self._build_api()
        task = self._make_task()
        result = api._format_fractal_event(task, OutputStrategy.REALTIME)

        assert result.startswith("id: evt-001\n")
        assert "event: node.thinking\n" in result
        assert "data: " in result
        assert result.endswith("\n\n")

    def test_realtime_data_contains_fractal_fields(self):
        api = self._build_api()
        task = self._make_task()
        result = api._format_fractal_event(task, OutputStrategy.REALTIME)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["task_id"] == "evt-001"
        assert data["action"] == "node.thinking"
        assert data["node_id"] == "w1"
        assert data["node_path"] == "root/w1"
        assert data["depth"] == 1
        assert data["parent_node_id"] == "root"
        assert data["status"] == "running"
        assert "display" not in data

    def test_tree_adds_display_field(self):
        api = self._build_api()
        task = self._make_task()
        result = api._format_fractal_event(task, OutputStrategy.TREE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert "display" in data

    def test_tree_display_has_correct_indent(self):
        api = self._build_api()
        # w1 is at depth 1 -> indent = "  " (2 spaces)
        task = self._make_task(node_id="w1", content="thinking hard")
        result = api._format_fractal_event(task, OutputStrategy.TREE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["display"].startswith("  [w1]")

    def test_tree_display_deeper_indent(self):
        api = self._build_api()
        # sub1 is at depth 2 -> indent = "    " (4 spaces)
        task = self._make_task(node_id="sub1", content="sub-thinking")
        result = api._format_fractal_event(task, OutputStrategy.TREE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["display"].startswith("    [sub1]")

    def test_tree_display_root_no_indent(self):
        api = self._build_api()
        # root is at depth 0 -> no indent
        task = self._make_task(node_id="root", content="root thinking")
        result = api._format_fractal_event(task, OutputStrategy.TREE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["display"].startswith("[root]")

    def test_tree_content_truncated_to_50_chars(self):
        api = self._build_api()
        long_content = "A" * 100
        task = self._make_task(node_id="w1", content=long_content)
        result = api._format_fractal_event(task, OutputStrategy.TREE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        # display should contain exactly 50 A's, not 100
        display = data["display"]
        assert "A" * 50 in display
        assert "A" * 51 not in display

    def test_tree_empty_content(self):
        api = self._build_api()
        task = self._make_task(node_id="w1", content="")
        result = api._format_fractal_event(task, OutputStrategy.TREE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["display"] == "  [w1] ..."

    def test_tree_no_content_key(self):
        api = self._build_api()
        task = Task(
            taskId="evt-002",
            action="node.tool_call",
            parameters={"node_id": "w1"},
            status=TaskStatus.RUNNING,
        )
        result = api._format_fractal_event(task, OutputStrategy.TREE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        # content defaults to "" when key is missing
        assert data["display"] == "  [w1] ..."

    def test_by_node_strategy_same_as_realtime(self):
        api = self._build_api()
        task = self._make_task()
        realtime_result = api._format_fractal_event(task, OutputStrategy.REALTIME)
        by_node_result = api._format_fractal_event(task, OutputStrategy.BY_NODE)

        # Both non-TREE strategies produce the same output (no display field)
        assert realtime_result == by_node_result

    def test_unknown_node_id_defaults(self):
        api = self._build_api()
        task = Task(
            taskId="evt-003",
            action="node.thinking",
            parameters={},  # no node_id at all
            status=TaskStatus.PENDING,
        )
        result = api._format_fractal_event(task, OutputStrategy.REALTIME)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        # node_id defaults to "unknown" in _format_fractal_event
        assert data["node_path"] == "unknown"
        assert data["depth"] == 0
        assert data["parent_node_id"] is None

    def test_event_id_in_sse(self):
        api = self._build_api()
        task = self._make_task(taskId="unique-id-999")
        result = api._format_fractal_event(task, OutputStrategy.REALTIME)

        assert "id: unique-id-999\n" in result

    def test_unicode_content_preserved(self):
        api = self._build_api()
        task = self._make_task(content="thinking about unicode")
        result = api._format_fractal_event(task, OutputStrategy.REALTIME)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["parameters"]["content"] == "thinking about unicode"


# ==================== _format_connected_event ====================


class TestFormatConnectedEvent:
    """Tests for FractalStreamAPI._format_connected_event."""

    def test_basic_connected_event(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_connected_event(OutputStrategy.REALTIME)

        assert "event: connected\n" in result
        assert result.endswith("\n\n")

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["status"] == "connected"
        assert data["strategy"] == "realtime"

    def test_connected_event_tree_strategy(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_connected_event(OutputStrategy.TREE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["strategy"] == "tree"

    def test_connected_event_by_node_strategy(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_connected_event(OutputStrategy.BY_NODE)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["strategy"] == "by_node"

    def test_connected_event_no_extra(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_connected_event(OutputStrategy.REALTIME)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        # Only status and strategy keys when no extra
        assert set(data.keys()) == {"status", "strategy"}

    def test_connected_event_with_extra(self):
        api = FractalStreamAPI(EventBus())
        extra = {"node_id": "w1", "include_children": True}
        result = api._format_connected_event(OutputStrategy.REALTIME, extra)

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["status"] == "connected"
        assert data["strategy"] == "realtime"
        assert data["node_id"] == "w1"
        assert data["include_children"] is True

    def test_connected_event_with_empty_extra(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_connected_event(OutputStrategy.REALTIME, {})

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert set(data.keys()) == {"status", "strategy"}

    def test_connected_event_no_id_field(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_connected_event(OutputStrategy.REALTIME)

        # SSEFormatter only adds id line when event_id is provided; _format_connected_event
        # does not pass event_id, so there should be no "id:" line.
        lines = result.split("\n")
        assert not any(line.startswith("id:") for line in lines)


# ==================== _format_disconnected_event ====================


class TestFormatDisconnectedEvent:
    """Tests for FractalStreamAPI._format_disconnected_event."""

    def test_disconnected_event_structure(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_disconnected_event()

        assert "event: disconnected\n" in result
        assert result.endswith("\n\n")

    def test_disconnected_event_data(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_disconnected_event()

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data == {"status": "disconnected"}

    def test_disconnected_event_no_id_field(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_disconnected_event()

        lines = result.split("\n")
        assert not any(line.startswith("id:") for line in lines)


# ==================== _format_heartbeat ====================


class TestFormatHeartbeat:
    """Tests for FractalStreamAPI._format_heartbeat (requires event loop)."""

    @pytest.mark.asyncio
    async def test_heartbeat_event_structure(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_heartbeat()

        assert "event: heartbeat\n" in result
        assert result.endswith("\n\n")

    @pytest.mark.asyncio
    async def test_heartbeat_contains_timestamp(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_heartbeat()

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert "timestamp" in data
        assert isinstance(data["timestamp"], (int, float))

    @pytest.mark.asyncio
    async def test_heartbeat_timestamp_is_non_negative(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_heartbeat()

        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        data = json.loads(data_line[len("data: "):])

        assert data["timestamp"] >= 0

    @pytest.mark.asyncio
    async def test_heartbeat_no_id_field(self):
        api = FractalStreamAPI(EventBus())
        result = api._format_heartbeat()

        lines = result.split("\n")
        assert not any(line.startswith("id:") for line in lines)
