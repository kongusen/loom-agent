"""
Tests for SandboxToolManager

测试沙盒工具管理器的核心功能：
- 工具注册/注销
- 工具执行
- 作用域隔离
- MCP 服务器集成
"""

import pytest

from loom.events import EventBus
from loom.protocol.mcp import MCPToolDefinition
from loom.tools.sandbox import Sandbox
from loom.tools.sandbox_manager import SandboxToolManager, ToolScope, ToolWrapper


class TestToolScope:
    """测试 ToolScope 枚举"""

    def test_tool_scope_values(self):
        """测试作用域枚举值"""
        assert ToolScope.SANDBOXED.value == "sandboxed"
        assert ToolScope.SYSTEM.value == "system"
        assert ToolScope.MCP.value == "mcp"
        assert ToolScope.CONTEXT.value == "context"


class TestToolWrapper:
    """测试 ToolWrapper"""

    @pytest.mark.asyncio
    async def test_wrapper_sandboxed_execution(self, tmp_path):
        """测试沙盒化工具执行"""
        sandbox = Sandbox(tmp_path)
        (tmp_path / "test.txt").write_text("Hello")

        async def read_func(path: str, sandbox: Sandbox) -> str:
            return sandbox.safe_read(path)

        definition = MCPToolDefinition(
            name="read_file",
            description="Read a file",
            inputSchema={},
        )

        wrapper = ToolWrapper(
            name="read_file",
            func=read_func,
            definition=definition,
            scope=ToolScope.SANDBOXED,
        )

        result = await wrapper.execute({"path": "test.txt"}, sandbox=sandbox)
        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_wrapper_direct_execution(self):
        """测试直接执行（不注入沙盒）"""

        async def system_func(value: int) -> int:
            return value * 2

        definition = MCPToolDefinition(
            name="double",
            description="Double a value",
            inputSchema={},
        )

        wrapper = ToolWrapper(
            name="double",
            func=system_func,
            definition=definition,
            scope=ToolScope.SYSTEM,
        )

        result = await wrapper.execute({"value": 5})
        assert result == 10


class TestSandboxToolManagerInit:
    """测试 SandboxToolManager 初始化"""

    def test_init_with_sandbox(self, tmp_path):
        """测试使用沙盒初始化"""
        sandbox = Sandbox(tmp_path)
        manager = SandboxToolManager(sandbox)

        assert manager.sandbox == sandbox
        assert manager.event_bus is None
        assert len(manager) == 0

    def test_init_with_event_bus(self, tmp_path):
        """测试带事件总线初始化"""
        sandbox = Sandbox(tmp_path)
        event_bus = EventBus()
        manager = SandboxToolManager(sandbox, event_bus=event_bus)

        assert manager.event_bus == event_bus


class TestSandboxToolManagerRegister:
    """测试工具注册"""

    @pytest.fixture
    def manager(self, tmp_path):
        """创建管理器实例"""
        sandbox = Sandbox(tmp_path)
        return SandboxToolManager(sandbox)

    @pytest.mark.asyncio
    async def test_register_tool(self, manager):
        """测试注册工具"""

        async def dummy_func(arg: str) -> str:
            return arg

        definition = MCPToolDefinition(
            name="dummy",
            description="Dummy tool",
            inputSchema={},
        )

        await manager.register_tool("dummy", dummy_func, definition, ToolScope.SANDBOXED)

        assert "dummy" in manager
        assert len(manager) == 1

    @pytest.mark.asyncio
    async def test_register_duplicate_tool_raises_error(self, manager):
        """测试注册重复工具抛出错误"""

        async def dummy_func(arg: str) -> str:
            return arg

        definition = MCPToolDefinition(
            name="dummy",
            description="Dummy tool",
            inputSchema={},
        )

        await manager.register_tool("dummy", dummy_func, definition, ToolScope.SANDBOXED)

        with pytest.raises(ValueError, match="already registered"):
            await manager.register_tool("dummy", dummy_func, definition, ToolScope.SANDBOXED)

    def test_unregister_tool(self, manager):
        """测试注销工具"""
        # 这个测试需要先注册一个工具，但由于注册是异步的，
        # 我们在这里只测试注销逻辑
        # 在实际使用中，工具会被先注册
        manager._tools["dummy"] = None  # Mock registration

        result = manager.unregister_tool("dummy")
        assert result is True
        assert "dummy" not in manager

    def test_unregister_nonexistent_tool(self, manager):
        """测试注销不存在的工具"""
        result = manager.unregister_tool("nonexistent")
        assert result is False


class TestSandboxToolManagerExecute:
    """测试工具执行"""

    @pytest.fixture
    def manager(self, tmp_path):
        """创建管理器实例"""
        sandbox = Sandbox(tmp_path)
        return SandboxToolManager(sandbox)

    @pytest.mark.asyncio
    async def test_execute_sandboxed_tool(self, manager, tmp_path):
        """测试执行沙盒化工具"""
        (tmp_path / "test.txt").write_text("Hello, World!")

        async def read_func(path: str, sandbox: Sandbox) -> str:
            return sandbox.safe_read(path)

        definition = MCPToolDefinition(
            name="read_file",
            description="Read file",
            inputSchema={},
        )

        await manager.register_tool("read_file", read_func, definition, ToolScope.SANDBOXED)

        result = await manager.execute_tool("read_file", {"path": "test.txt"})
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_execute_system_tool(self, manager):
        """测试执行系统工具"""

        async def double_func(value: int) -> int:
            return value * 2

        definition = MCPToolDefinition(
            name="double",
            description="Double value",
            inputSchema={},
        )

        await manager.register_tool("double", double_func, definition, ToolScope.SYSTEM)

        result = await manager.execute_tool("double", {"value": 21})
        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool_raises_error(self, manager):
        """测试执行不存在的工具抛出错误"""
        with pytest.raises(ValueError, match="not found"):
            await manager.execute_tool("nonexistent", {})

    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self, manager):
        """测试工具执行错误"""

        async def failing_func() -> str:
            raise ValueError("Tool failed")

        definition = MCPToolDefinition(
            name="failing",
            description="Failing tool",
            inputSchema={},
        )

        await manager.register_tool("failing", failing_func, definition, ToolScope.SYSTEM)

        with pytest.raises(ValueError, match="Tool failed"):
            await manager.execute_tool("failing", {})


class TestSandboxToolManagerList:
    """测试工具列表功能"""

    @pytest.fixture
    def manager(self, tmp_path):
        """创建管理器实例"""
        sandbox = Sandbox(tmp_path)
        return SandboxToolManager(sandbox)

    @pytest.mark.asyncio
    async def test_list_tools(self, manager):
        """测试列出所有工具"""

        async def dummy1() -> str:
            return "1"

        async def dummy2() -> str:
            return "2"

        definition1 = MCPToolDefinition(name="dummy1", description="Dummy 1", inputSchema={})
        definition2 = MCPToolDefinition(name="dummy2", description="Dummy 2", inputSchema={})

        await manager.register_tool("dummy1", dummy1, definition1, ToolScope.SANDBOXED)
        await manager.register_tool("dummy2", dummy2, definition2, ToolScope.SYSTEM)

        tools = manager.list_tools()
        assert len(tools) == 2
        assert tools[0].name == "dummy1"
        assert tools[1].name == "dummy2"

    @pytest.mark.asyncio
    async def test_list_tool_names(self, manager):
        """测试列出工具名称"""

        async def dummy() -> str:
            return "dummy"

        definition = MCPToolDefinition(name="dummy", description="Dummy", inputSchema={})

        await manager.register_tool("dummy", dummy, definition, ToolScope.SANDBOXED)

        names = manager.list_tool_names()
        assert names == ["dummy"]

    @pytest.mark.asyncio
    async def test_get_tools_by_scope(self, manager):
        """测试按作用域获取工具"""

        async def dummy1() -> str:
            return "1"

        async def dummy2() -> str:
            return "2"

        definition1 = MCPToolDefinition(name="dummy1", description="Dummy 1", inputSchema={})
        definition2 = MCPToolDefinition(name="dummy2", description="Dummy 2", inputSchema={})

        await manager.register_tool("dummy1", dummy1, definition1, ToolScope.SANDBOXED)
        await manager.register_tool("dummy2", dummy2, definition2, ToolScope.SYSTEM)

        sandboxed_tools = manager.get_tools_by_scope(ToolScope.SANDBOXED)
        system_tools = manager.get_tools_by_scope(ToolScope.SYSTEM)

        assert len(sandboxed_tools) == 1
        assert sandboxed_tools[0].name == "dummy1"
        assert len(system_tools) == 1
        assert system_tools[0].name == "dummy2"

    def test_get_tool(self, manager):
        """测试获取工具包装器"""

        async def dummy() -> str:
            return "dummy"

        definition = MCPToolDefinition(name="dummy", description="Dummy", inputSchema={})

        # 直接添加到内部字典（绕过异步注册）
        manager._tools["dummy"] = ToolWrapper(
            name="dummy",
            func=dummy,
            definition=definition,
            scope=ToolScope.SANDBOXED,
        )

        wrapper = manager.get_tool("dummy")
        assert wrapper is not None
        assert wrapper.name == "dummy"
        assert wrapper.scope == ToolScope.SANDBOXED

    def test_get_nonexistent_tool(self, manager):
        """测试获取不存在的工具"""
        wrapper = manager.get_tool("nonexistent")
        assert wrapper is None


class TestSandboxToolManagerContains:
    """测试工具存在性检查"""

    @pytest.fixture
    def manager(self, tmp_path):
        """创建管理器实例"""
        sandbox = Sandbox(tmp_path)
        return SandboxToolManager(sandbox)

    @pytest.mark.asyncio
    async def test_contains_registered_tool(self, manager):
        """测试检查已注册的工具"""

        async def dummy() -> str:
            return "dummy"

        definition = MCPToolDefinition(name="dummy", description="Dummy", inputSchema={})

        await manager.register_tool("dummy", dummy, definition, ToolScope.SANDBOXED)

        assert "dummy" in manager

    def test_contains_nonexistent_tool(self, manager):
        """测试检查不存在的工具"""
        assert "nonexistent" not in manager


class TestSandboxToolManagerMCP:
    """测试 MCP 服务器集成"""

    @pytest.fixture
    def manager(self, tmp_path):
        """创建管理器实例"""
        sandbox = Sandbox(tmp_path)
        event_bus = EventBus()
        return SandboxToolManager(sandbox, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_mcp_adapter_property(self, manager):
        """测试 MCP 适配器属性"""
        # 初始时应该为 None
        assert manager.mcp_adapter is None

    @pytest.mark.asyncio
    async def test_mcp_adapter_created_after_registration(self, manager):
        """测试注册 MCP 服务器后创建适配器"""
        # 导入 MCPToolResult
        from loom.protocol.mcp import MCPToolResult

        # 创建一个 mock MCP 服务器
        class MockMCPServer:
            async def list_tools(self):
                return [
                    MCPToolDefinition(
                        name="mcp_tool",
                        description="MCP tool",
                        inputSchema={},
                    )
                ]

            async def call_tool(self, name, args):
                # 返回正确的 MCPToolResult 格式
                return MCPToolResult(
                    content=[{"type": "text", "text": f"Called {name} with {args}"}],
                    is_error=False,
                )

        server = MockMCPServer()

        # 注册 MCP 服务器
        await manager.register_mcp_server("test_server", server)

        # 适配器应该被创建
        assert manager.mcp_adapter is not None

        # MCP 工具应该被注册
        assert "mcp_tool" in manager

        # 可以执行 MCP 工具
        result = await manager.execute_tool("mcp_tool", {"arg": "value"})
        # MCP 适配器返回 content 字段
        assert "Called mcp_tool" in str(result)
