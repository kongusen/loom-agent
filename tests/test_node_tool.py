"""
Tests for Tool Node

Tests the ToolNode class which wraps MCP tools as nodes.
"""

from unittest.mock import Mock

import pytest

from loom.kernel.core.dispatcher import Dispatcher
from loom.node.tool import ToolNode
from loom.protocol.cloudevents import CloudEvent
from loom.protocol.mcp import MCPToolDefinition


class TestToolNode:
    """Test ToolNode functionality."""

    @pytest.fixture
    async def dispatcher(self):
        """Create a Dispatcher with a test bus."""
        from loom.kernel.core.bus import UniversalEventBus

        bus = UniversalEventBus()
        await bus.connect()
        dispatcher = Dispatcher(bus)
        yield dispatcher
        await bus.disconnect()

    def test_initialization(self, dispatcher):
        """Test tool node initialization."""
        tool_def = Mock(spec=MCPToolDefinition)
        tool_def.name = "test_tool"

        def func(args):
            return "result"

        node = ToolNode("test_node", dispatcher, tool_def, func)
        assert node.node_id == "test_node"
        assert node.tool_def == tool_def
        assert node.func == func

    @pytest.mark.asyncio
    async def test_process_with_arguments(self, dispatcher):
        """Test processing with arguments."""
        tool_def = Mock(spec=MCPToolDefinition)

        def func(args):
            return f"processed: {args.get('input')}"

        node = ToolNode("test_node", dispatcher, tool_def, func)

        event = CloudEvent.create(
            source="/caller", type="node.request", data={"arguments": {"input": "test_data"}}
        )

        result = await node.process(event)
        assert result == {"result": "processed: test_data"}

    @pytest.mark.asyncio
    async def test_process_without_arguments(self, dispatcher):
        """Test processing without arguments."""
        tool_def = Mock(spec=MCPToolDefinition)

        def func(args):
            return f"got: {args}"

        node = ToolNode("test_node", dispatcher, tool_def, func)

        event = CloudEvent.create(source="/caller", type="node.request", data={"arguments": {}})

        result = await node.process(event)
        assert result == {"result": "got: {}"}

    @pytest.mark.asyncio
    async def test_process_with_async_function(self, dispatcher):
        """Test processing with async function."""
        import asyncio

        tool_def = Mock(spec=MCPToolDefinition)

        async def async_func(args):
            await asyncio.sleep(0.01)
            return f"async result: {args.get('value')}"

        node = ToolNode("test_node", dispatcher, tool_def, async_func)

        event = CloudEvent.create(
            source="/caller", type="node.request", data={"arguments": {"value": 42}}
        )

        result = await node.process(event)
        assert result == {"result": "async result: 42"}

    @pytest.mark.asyncio
    async def test_process_with_sync_function(self, dispatcher):
        """Test processing with sync function."""
        tool_def = Mock(spec=MCPToolDefinition)

        def sync_func(args):
            return f"sync result: {args.get('data')}"

        node = ToolNode("test_node", dispatcher, tool_def, sync_func)

        event = CloudEvent.create(
            source="/caller", type="node.request", data={"arguments": {"data": "test"}}
        )

        result = await node.process(event)
        assert result == {"result": "sync result: test"}

    @pytest.mark.asyncio
    async def test_process_with_error(self, dispatcher):
        """Test processing when function raises error."""
        tool_def = Mock(spec=MCPToolDefinition)

        def failing_func(args):
            raise ValueError("Test error")

        node = ToolNode("test_node", dispatcher, tool_def, failing_func)

        event = CloudEvent.create(source="/caller", type="node.request", data={"arguments": {}})

        with pytest.raises(RuntimeError, match="Tool execution failed"):
            await node.process(event)

    @pytest.mark.asyncio
    async def test_process_with_complex_return_value(self, dispatcher):
        """Test processing with complex return value."""
        tool_def = Mock(spec=MCPToolDefinition)

        def complex_func(args):
            return {"status": "success", "data": [1, 2, 3], "nested": {"key": "value"}}

        node = ToolNode("test_node", dispatcher, tool_def, complex_func)

        event = CloudEvent.create(source="/caller", type="node.request", data={"arguments": {}})

        result = await node.process(event)
        assert result == {
            "result": {"status": "success", "data": [1, 2, 3], "nested": {"key": "value"}}
        }

    @pytest.mark.asyncio
    async def test_process_with_none_return(self, dispatcher):
        """Test processing with None return value."""
        tool_def = Mock(spec=MCPToolDefinition)

        def none_func(args):
            return None

        node = ToolNode("test_node", dispatcher, tool_def, none_func)

        event = CloudEvent.create(source="/caller", type="node.request", data={"arguments": {}})

        result = await node.process(event)
        assert result == {"result": None}

    @pytest.mark.asyncio
    async def test_process_with_exception_in_async_func(self, dispatcher):
        """Test processing when async function raises error."""
        import asyncio

        tool_def = Mock(spec=MCPToolDefinition)

        async def failing_async_func(args):
            await asyncio.sleep(0.01)
            raise RuntimeError("Async failure")

        node = ToolNode("test_node", dispatcher, tool_def, failing_async_func)

        event = CloudEvent.create(source="/caller", type="node.request", data={"arguments": {}})

        with pytest.raises(RuntimeError, match="Tool execution failed"):
            await node.process(event)

    @pytest.mark.asyncio
    async def test_process_with_various_argument_types(self, dispatcher):
        """Test processing with various argument types."""
        tool_def = Mock(spec=MCPToolDefinition)

        def type_check_func(args):
            return {
                "string": str(args.get("string", "")),
                "number": float(args.get("number", 0)),
                "boolean": bool(args.get("boolean", False)),
                "list": list(args.get("list", [])),
                "none": args.get("none") is None,
            }

        node = ToolNode("test_node", dispatcher, tool_def, type_check_func)

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={
                "arguments": {
                    "string": "test",
                    "number": 42,
                    "boolean": True,
                    "list": [1, 2, 3],
                    "none": None,
                }
            },
        )

        result = await node.process(event)
        expected = {
            "result": {
                "string": "test",
                "number": 42.0,
                "boolean": True,
                "list": [1, 2, 3],
                "none": True,
            }
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_process_preserves_error_details(self, dispatcher):
        """Test that error details are preserved."""
        tool_def = Mock(spec=MCPToolDefinition)

        def detailed_error_func(args):
            raise ValueError("Detailed error message with context")

        node = ToolNode("test_node", dispatcher, tool_def, detailed_error_func)

        event = CloudEvent.create(source="/caller", type="node.request", data={"arguments": {}})

        with pytest.raises(RuntimeError) as exc_info:
            await node.process(event)

        assert "Detailed error message with context" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_with_empty_args_dict(self, dispatcher):
        """Test processing when args dict is empty."""
        tool_def = Mock(spec=MCPToolDefinition)

        def empty_args_func(args):
            return {"args_length": len(args)}

        node = ToolNode("test_node", dispatcher, tool_def, empty_args_func)

        event = CloudEvent.create(source="/caller", type="node.request", data={})

        result = await node.process(event)
        assert result == {"result": {"args_length": 0}}

    @pytest.mark.asyncio
    async def test_process_returns_dict_wrapper(self, dispatcher):
        """Test that process always wraps result in dict."""
        tool_def = Mock(spec=MCPToolDefinition)

        def string_func(args):
            return "plain string"

        node = ToolNode("test_node", dispatcher, tool_def, string_func)

        event = CloudEvent.create(source="/caller", type="node.request", data={"arguments": {}})

        result = await node.process(event)
        assert isinstance(result, dict)
        assert "result" in result
        assert result["result"] == "plain string"
