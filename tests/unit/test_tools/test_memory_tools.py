"""
Tests for tools/memory modules: browse, events, manage
"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from loom.tools.memory.browse import (
    create_unified_browse_tool,
    execute_unified_browse_tool,
)
from loom.tools.memory.events import (
    _format_events,
    create_unified_events_tool,
    execute_unified_events_tool,
)
from loom.tools.memory.manage import (
    create_unified_manage_tool,
    execute_unified_manage_tool,
)

# ============ Browse Tool ============


class TestCreateUnifiedBrowseTool:
    def test_returns_function_tool(self):
        tool = create_unified_browse_tool()
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "browse_memory"

    def test_schema_has_required_fields(self):
        tool = create_unified_browse_tool()
        params = tool["function"]["parameters"]
        assert "action" in params["properties"]
        assert "layer" in params["properties"]
        assert params["required"] == ["action"]


class TestExecuteBrowseTool:
    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        entry1 = MagicMock()
        entry1.content = "tool_call: search for files on disk"
        entry1.entry_id = "e1"
        entry1.importance = 0.8
        entry1.tags = ["tool"]
        entry2 = MagicMock()
        entry2.content = "thinking about the problem"
        entry2.entry_id = "e2"
        entry2.importance = 0.6
        entry2.tags = []
        session.memory = MagicMock()
        session.memory.get_working_memory = MagicMock(return_value=[entry1, entry2])
        return session

    @pytest.fixture
    def mock_cc(self):
        cc = MagicMock()
        cc.get_l3_summaries.return_value = [
            {"content": "Summary of agent actions in session", "timestamp": "2025-01-01T00:00:00"},
            {"content": "Short", "timestamp": "2025-01-02T00:00:00"},
        ]
        return cc

    async def test_list_l2(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "list", "layer": "L2"}, mock_session, mock_cc
        )
        assert result["layer"] == "L2"
        assert result["action"] == "list"
        assert result["count"] == 2
        assert result["items"][0]["index"] == 1

    async def test_list_l3(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "list", "layer": "L3"}, mock_session, mock_cc
        )
        assert result["layer"] == "L3"
        assert result["count"] == 2

    async def test_select_l2(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "select", "layer": "L2", "indices": [1]}, mock_session, mock_cc
        )
        assert result["layer"] == "L2"
        assert result["action"] == "select"
        assert result["count"] == 1
        assert result["selected"][0]["entry_id"] == "e1"

    async def test_select_l3(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "select", "layer": "L3", "indices": [1, 2]}, mock_session, mock_cc
        )
        assert result["layer"] == "L3"
        assert result["count"] == 2

    async def test_select_no_indices(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "select", "layer": "L2"}, mock_session, mock_cc
        )
        assert "error" in result

    async def test_select_out_of_range(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "select", "layer": "L2", "indices": [99]}, mock_session, mock_cc
        )
        assert result["count"] == 0

    async def test_invalid_action(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "delete"}, mock_session, mock_cc
        )
        assert "error" in result

    async def test_default_layer_is_l2(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "list"}, mock_session, mock_cc
        )
        assert result["layer"] == "L2"

    async def test_l3_preview_truncation(self, mock_session, mock_cc):
        result = await execute_unified_browse_tool(
            {"action": "list", "layer": "L3"}, mock_session, mock_cc
        )
        # First item has content > 50 chars, should be truncated
        first = result["items"][0]
        assert "..." in first["preview"] or len(first["preview"]) <= 53


# ============ Events Tool ============


class TestCreateUnifiedEventsTool:
    def test_returns_function_tool(self):
        tool = create_unified_events_tool()
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "query_events"

    def test_schema_has_filter_by(self):
        tool = create_unified_events_tool()
        params = tool["function"]["parameters"]
        assert "filter_by" in params["properties"]
        assert params["required"] == ["filter_by"]

    def test_filter_by_enum(self):
        tool = create_unified_events_tool()
        enum = tool["function"]["parameters"]["properties"]["filter_by"]["enum"]
        assert set(enum) == {"action", "node", "target", "recent", "thinking"}


class TestFormatEvents:
    def test_format_events_basic(self):
        event = MagicMock()
        event.task_id = "t1"
        event.action = "node.tool_call"
        event.parameters = {"tool": "search"}
        event.result = "ok"
        event.status = MagicMock(value="completed")
        event.created_at = MagicMock()
        event.created_at.isoformat.return_value = "2025-01-01T00:00:00"
        result = _format_events([event])
        assert len(result) == 1
        assert result[0]["task_id"] == "t1"
        assert result[0]["action"] == "node.tool_call"

    def test_format_events_none_status(self):
        event = MagicMock()
        event.task_id = "t1"
        event.action = "test"
        event.parameters = {}
        event.result = None
        event.status = None
        event.created_at = None
        result = _format_events([event])
        assert result[0]["status"] is None
        assert result[0]["created_at"] is None

    def test_format_events_empty(self):
        assert _format_events([]) == []


class TestExecuteUnifiedEventsTool:
    @pytest.fixture
    def mock_event_bus(self):
        bus = MagicMock()
        e1 = MagicMock()
        e1.action = "node.tool_call"
        e1.task_id = "t1"
        e1.parameters = {"tool": "search"}
        e1.result = "ok"
        e1.status = MagicMock(value="completed")
        e1.created_at = MagicMock()
        e1.created_at.isoformat.return_value = "2025-01-01"
        e1.source_node = "agent-1"
        e1.target_agent = None
        e1.target_node = None

        e2 = MagicMock()
        e2.action = "node.thinking"
        e2.task_id = "t2"
        e2.parameters = {"content": "I should search"}
        e2.result = None
        e2.status = MagicMock(value="completed")
        e2.created_at = MagicMock()
        e2.created_at.isoformat.return_value = "2025-01-02"
        e2.source_node = "agent-1"
        e2.target_agent = "agent-2"
        e2.target_node = "agent-2"

        bus.get_recent_events.return_value = [e1, e2]
        return bus

    async def test_filter_by_action(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "action", "action": "node.tool_call"}, mock_event_bus
        )
        assert result["filter_by"] == "action"
        assert result["count"] == 1

    async def test_filter_by_node(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "node", "node_id": "agent-1"}, mock_event_bus
        )
        assert result["filter_by"] == "node"
        assert result["count"] == 2

    async def test_filter_by_target(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "target", "target_agent": "agent-2"}, mock_event_bus
        )
        assert result["filter_by"] == "target"
        assert result["count"] == 1

    async def test_filter_by_target_no_args(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "target"}, mock_event_bus
        )
        assert "error" in result

    async def test_filter_by_recent(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "recent"}, mock_event_bus
        )
        assert result["filter_by"] == "recent"
        assert result["count"] == 2

    async def test_filter_by_thinking(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "thinking"}, mock_event_bus
        )
        assert result["filter_by"] == "thinking"
        assert result["count"] == 1
        assert result["thoughts"][0]["content"] == "I should search"

    async def test_invalid_filter(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "invalid"}, mock_event_bus
        )
        assert "error" in result

    async def test_limit_parameter(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "recent", "limit": 1}, mock_event_bus
        )
        assert result["count"] == 1

    async def test_filter_by_action_with_node(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "action", "action": "node.tool_call", "node_id": "agent-1"},
            mock_event_bus,
        )
        assert result["count"] == 1

    async def test_filter_by_target_with_node_id(self, mock_event_bus):
        result = await execute_unified_events_tool(
            {"filter_by": "target", "node_id": "agent-2"}, mock_event_bus
        )
        assert result["count"] == 1


# ============ Manage Tool ============


class TestCreateUnifiedManageTool:
    def test_returns_function_tool(self):
        tool = create_unified_manage_tool()
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "manage_memory"

    def test_schema_has_action(self):
        tool = create_unified_manage_tool()
        params = tool["function"]["parameters"]
        assert "action" in params["properties"]
        assert params["required"] == ["action"]

    def test_action_enum(self):
        tool = create_unified_manage_tool()
        enum = tool["function"]["parameters"]["properties"]["action"]["enum"]
        assert set(enum) == {"stats", "aggregate", "persist"}


class TestExecuteManageTool:
    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.session_id = "sess-1"
        session.get_stats.return_value = {"status": "active"}
        session.memory = MagicMock()
        session.memory.get_stats.return_value = {
            "l1_message_count": 3,
            "l1_token_usage": 500,
            "l2_entry_count": 2,
            "l2_token_usage": 200,
        }
        return session

    @pytest.fixture
    def mock_cc(self):
        cc = MagicMock()
        type(cc).l3_count = PropertyMock(return_value=5)
        type(cc).l3_token_usage = PropertyMock(return_value=1200)
        type(cc).session_ids = PropertyMock(return_value=["sess-1"])
        cc.aggregate_to_l3 = AsyncMock(return_value={"summary": "ok"})
        cc.persist_to_l4 = AsyncMock(return_value=True)
        return cc

    async def test_stats(self, mock_session, mock_cc):
        result = await execute_unified_manage_tool(
            {"action": "stats"}, mock_session, mock_cc
        )
        assert result["action"] == "stats"
        assert result["session"]["id"] == "sess-1"
        assert result["session"]["l2_entries"] == 2
        assert result["controller"]["l3_count"] == 5

    async def test_aggregate(self, mock_session, mock_cc):
        result = await execute_unified_manage_tool(
            {"action": "aggregate"}, mock_session, mock_cc
        )
        assert result["action"] == "aggregate"
        assert result["success"] is True

    async def test_aggregate_returns_none(self, mock_session, mock_cc):
        mock_cc.aggregate_to_l3 = AsyncMock(return_value=None)
        result = await execute_unified_manage_tool(
            {"action": "aggregate"}, mock_session, mock_cc
        )
        assert result["success"] is False

    async def test_persist(self, mock_session, mock_cc):
        result = await execute_unified_manage_tool(
            {"action": "persist"}, mock_session, mock_cc
        )
        assert result["action"] == "persist"
        assert result["success"] is True

    async def test_persist_failure(self, mock_session, mock_cc):
        mock_cc.persist_to_l4 = AsyncMock(return_value=False)
        result = await execute_unified_manage_tool(
            {"action": "persist"}, mock_session, mock_cc
        )
        assert result["success"] is False

    async def test_invalid_action(self, mock_session, mock_cc):
        result = await execute_unified_manage_tool(
            {"action": "invalid"}, mock_session, mock_cc
        )
        assert "error" in result

    async def test_default_action_is_stats(self, mock_session, mock_cc):
        result = await execute_unified_manage_tool({}, mock_session, mock_cc)
        assert result["action"] == "stats"
