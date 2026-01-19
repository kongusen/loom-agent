"""
Tests for MCP Adapter
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.events import EventBus
from loom.protocol.mcp import MCPServer, MCPToolDefinition, MCPToolResult
from loom.tools.mcp_adapter import MCPAdapter


class MockMCPServer(MCPServer):
    """Mock MCP Server for testing"""

    def __init__(self, tools: list[MCPToolDefinition] | None = None):
        self.tools = tools or []

    async def list_tools(self) -> list[MCPToolDefinition]:
        return self.tools

    async def call_tool(self, name: str, arguments: dict) -> MCPToolResult:
        return MCPToolResult(content=[{"result": "success"}], is_error=False)

    async def list_resources(self):
        return []

    async def read_resource(self, uri: str) -> str:
        return "resource content"

    async def list_prompts(self):
        return []

    async def get_prompt(self, name: str, arguments: dict) -> str:
        return "prompt content"


class TestMCPAdapter:
    """Test suite for MCPAdapter"""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus"""
        event_bus = AsyncMock(spec=EventBus)
        event_bus.publish = AsyncMock()
        return event_bus

    @pytest.fixture
    def adapter(self, mock_event_bus):
        """Create an MCP adapter instance"""
        return MCPAdapter(event_bus=mock_event_bus)

    @pytest.fixture
    def sample_tools(self):
        """Create sample tool definitions"""
        return [
            MCPToolDefinition(
                name="test_tool",
                description="A test tool",
                inputSchema={"type": "object"}
            ),
            MCPToolDefinition(
                name="another_tool",
                description="Another test tool",
                inputSchema={"type": "object"}
            )
        ]

    def test_init_without_event_bus(self):
        """Test initialization without event bus"""
        adapter = MCPAdapter()
        assert adapter.event_bus is None
        assert adapter.servers == {}
        assert adapter.tools == {}

    def test_init_with_event_bus(self, mock_event_bus):
        """Test initialization with event bus"""
        adapter = MCPAdapter(event_bus=mock_event_bus)
        assert adapter.event_bus is mock_event_bus
        assert adapter.servers == {}
        assert adapter.tools == {}

    @pytest.mark.asyncio
    async def test_register_server(self, adapter, sample_tools):
        """Test registering an MCP server"""
        server = MockMCPServer(tools=sample_tools)
        await adapter.register_server("test_server", server)

        assert "test_server" in adapter.servers
        assert adapter.servers["test_server"] is server

    @pytest.mark.asyncio
    async def test_register_server_discovers_tools(self, adapter, sample_tools):
        """Test that registering a server discovers its tools"""
        server = MockMCPServer(tools=sample_tools)
        await adapter.register_server("test_server", server)

        assert "test_tool" in adapter.tools
        assert "another_tool" in adapter.tools

    @pytest.mark.asyncio
    async def test_discover_tools(self, adapter, sample_tools):
        """Test discovering tools from a server"""
        server = MockMCPServer(tools=sample_tools)
        adapter.servers["test_server"] = server

        discovered = await adapter.discover_tools("test_server")

        assert len(discovered) == 2
        assert discovered[0].name == "test_tool"
        assert discovered[1].name == "another_tool"

    @pytest.mark.asyncio
    async def test_discover_tools_server_not_found(self, adapter):
        """Test discovering tools from non-existent server"""
        with pytest.raises(ValueError, match="Server not found: nonexistent"):
            await adapter.discover_tools("nonexistent")

    @pytest.mark.asyncio
    async def test_discover_tools_registers_tools(self, adapter, sample_tools):
        """Test that discovered tools are registered in the tools dict"""
        server = MockMCPServer(tools=sample_tools)
        adapter.servers["test_server"] = server

        await adapter.discover_tools("test_server")

        assert adapter.tools["test_tool"] == ("test_server", sample_tools[0])
        assert adapter.tools["another_tool"] == ("test_server", sample_tools[1])

    @pytest.mark.asyncio
    async def test_call_tool_success(self, adapter, mock_event_bus):
        """Test successfully calling a tool"""
        tool_def = MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object"}
        )
        server = MockMCPServer(tools=[tool_def])
        await adapter.register_server("test_server", server)

        result = await adapter.call_tool("test_tool", {"arg": "value"})

        assert result == [{"result": "success"}]
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, adapter):
        """Test calling a non-existent tool"""
        with pytest.raises(ValueError, match="Tool not found: nonexistent"):
            await adapter.call_tool("nonexistent", {})

    @pytest.mark.asyncio
    async def test_call_tool_server_not_found(self, adapter, sample_tools):
        """Test calling a tool when server is missing"""
        # Manually add a tool with a non-existent server
        adapter.tools["orphan_tool"] = ("missing_server", sample_tools[0])

        with pytest.raises(ValueError, match="Server not found: missing_server"):
            await adapter.call_tool("orphan_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_with_error(self, adapter, mock_event_bus):
        """Test calling a tool that returns an error"""
        tool_def = MCPToolDefinition(
            name="error_tool",
            description="An error tool",
            inputSchema={"type": "object"}
        )

        class ErrorServer(MockMCPServer):
            async def call_tool(self, name: str, arguments: dict) -> MCPToolResult:
                return MCPToolResult(
                    content=[{"error": "something went wrong"}],
                    is_error=True
                )

        server = ErrorServer(tools=[tool_def])
        await adapter.register_server("error_server", server)

        with pytest.raises(Exception, match="Tool execution failed"):
            await adapter.call_tool("error_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_sends_event(self, adapter, mock_event_bus):
        """Test that tool call sends an event"""
        tool_def = MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object"}
        )
        server = MockMCPServer(tools=[tool_def])
        await adapter.register_server("test_server", server)

        await adapter.call_tool("test_tool", {"arg": "value"})

        assert mock_event_bus.publish.call_count == 1

    def test_list_tools(self, adapter):
        """Test listing all registered tools"""
        adapter.tools = {
            "tool1": ("server1", MagicMock()),
            "tool2": ("server2", MagicMock()),
        }

        tools = adapter.list_tools()

        assert set(tools) == {"tool1", "tool2"}

    def test_list_tools_empty(self, adapter):
        """Test listing tools when none are registered"""
        tools = adapter.list_tools()
        assert tools == []

    def test_get_tool_definition(self, adapter):
        """Test getting a tool definition"""
        tool_def = MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object"}
        )
        adapter.tools["test_tool"] = ("server1", tool_def)

        result = adapter.get_tool_definition("test_tool")

        assert result is tool_def
        assert result.name == "test_tool"

    def test_get_tool_definition_not_found(self, adapter):
        """Test getting a non-existent tool definition"""
        result = adapter.get_tool_definition("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_servers(self, adapter, sample_tools):
        """Test managing multiple servers"""
        server1 = MockMCPServer(tools=[sample_tools[0]])
        server2 = MockMCPServer(tools=[sample_tools[1]])

        await adapter.register_server("server1", server1)
        await adapter.register_server("server2", server2)

        assert len(adapter.servers) == 2
        assert len(adapter.tools) == 2
        assert adapter.tools["test_tool"][0] == "server1"
        assert adapter.tools["another_tool"][0] == "server2"

    @pytest.mark.asyncio
    async def test_call_tool_without_event_bus(self):
        """Test calling a tool without event bus"""
        adapter = MCPAdapter(event_bus=None)
        tool_def = MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object"}
        )
        server = MockMCPServer(tools=[tool_def])
        await adapter.register_server("test_server", server)

        result = await adapter.call_tool("test_tool", {"arg": "value"})

        assert result == [{"result": "success"}]

    @pytest.mark.asyncio
    async def test_register_server_without_event_bus(self):
        """Test registering a server without event bus"""
        adapter = MCPAdapter(event_bus=None)
        tool_def = MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object"}
        )
        server = MockMCPServer(tools=[tool_def])

        await adapter.register_server("test_server", server)

        assert "test_server" in adapter.servers
        assert "test_tool" in adapter.tools
