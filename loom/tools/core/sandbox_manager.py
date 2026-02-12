"""
Sandbox Tool Manager - 沙盒工具管理器

基于公理系统实现统一的工具注册和执行中心：
- 所有工具通过统一接口注册
- 支持动态工具注册/注销
- MCP 工具无缝集成
- 自动沙盒化（文件操作受沙盒约束）

设计原则：
1. 统一接口 - 所有工具通过相同方式注册和执行
2. 作用域隔离 - 不同工具类型有不同的安全策略
3. 动态注册 - 支持运行时添加/移除工具
4. 向后兼容 - 现有工具可以平滑迁移
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loom.events import EventBus
from loom.tools.core.mcp_adapter import MCPAdapter
from loom.tools.core.sandbox import Sandbox
from loom.tools.mcp_types import MCPToolDefinition


class ToolScope(Enum):
    """
    工具作用域 - 定义工具的安全策略

    Attributes:
        SANDBOXED: 文件操作受沙盒约束 (file tools, search, todo)
        SYSTEM: 系统级操作，不受沙盒约束 (bash, http)
        MCP: 外部 MCP 工具
        CONTEXT: 上下文查询工具 (memory queries, event queries)
    """

    SANDBOXED = "sandboxed"  # 文件操作，受沙盒约束
    SYSTEM = "system"  # 系统操作，不受文件系统沙盒约束
    MCP = "mcp"  # 外部 MCP 工具
    CONTEXT = "context"  # 上下文查询工具


@dataclass
class ToolWrapper:
    """
    工具包装器 - 统一的工具表示

    Attributes:
        name: 工具名称
        func: 工具执行函数
        definition: MCP 格式的工具定义
        scope: 工具作用域
        metadata: 额外的元数据
        server_id: MCP 服务器 ID（仅 MCP 工具）
    """

    name: str
    func: Callable
    definition: MCPToolDefinition
    scope: ToolScope
    metadata: dict[str, Any] = field(default_factory=dict)
    server_id: str | None = None  # For MCP tools

    async def execute(self, args: dict, sandbox: Sandbox | None = None) -> Any:
        """
        执行工具，根据作用域应用相应的安全策略

        Args:
            args: 工具参数
            sandbox: 沙盒实例（仅 SANDBOXED 作用域需要）

        Returns:
            工具执行结果
        """
        # 对于沙盒化工具，自动注入 sandbox 参数
        if self.scope == ToolScope.SANDBOXED and sandbox is not None:
            return await self._execute_sandboxed(args, sandbox)
        else:
            # 直接调用
            return await self._execute_direct(args)

    async def _execute_sandboxed(self, args: dict, sandbox: Sandbox) -> Any:
        """执行沙盒化工具"""
        import inspect

        sig = inspect.signature(self.func)
        if "sandbox" in sig.parameters:
            # 检查是否是异步函数
            if inspect.iscoroutinefunction(self.func):
                return await self.func(**args, sandbox=sandbox)
            else:
                return self.func(**args, sandbox=sandbox)
        else:
            # 函数不需要 sandbox，可能是已绑定的方法
            if inspect.iscoroutinefunction(self.func):
                return await self.func(**args)
            else:
                return self.func(**args)

    async def _execute_direct(self, args: dict) -> Any:
        """直接执行工具（不注入 sandbox）"""
        import inspect

        if inspect.iscoroutinefunction(self.func):
            return await self.func(**args)
        else:
            return self.func(**args)


class SandboxToolManager:
    """
    沙盒工具管理器 - 统一的工具注册和执行中心

    这是新的工具系统核心，替代原有的分散式工具注册方式。

    功能：
    - 注册/注销工具
    - 执行工具
    - 集成 MCP 服务器
    - 列出所有工具

    示例:
        manager = SandboxToolManager(sandbox)
        await manager.register_tool("read_file", read_func, definition, ToolScope.SANDBOXED)
        result = await manager.execute_tool("read_file", {"path": "test.txt"})
    """

    def __init__(
        self,
        sandbox: Sandbox,
        event_bus: EventBus | None = None,
    ):
        """
        初始化沙盒工具管理器

        Args:
            sandbox: 沙盒实例
            event_bus: 事件总线（可选，用于发布工具执行事件）
        """
        self.sandbox = sandbox
        self.event_bus = event_bus
        self._tools: dict[str, ToolWrapper] = {}
        self._mcp_adapter: MCPAdapter | None = None

    async def register_tool(
        self,
        name: str,
        func: Callable,
        definition: MCPToolDefinition,
        scope: ToolScope = ToolScope.SANDBOXED,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称（唯一标识）
            func: 工具执行函数（async 函数）
            definition: MCP 格式的工具定义
            scope: 工具作用域
            metadata: 额外的元数据

        Raises:
            ValueError: 工具名称已存在
        """
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")

        wrapper = ToolWrapper(
            name=name,
            func=func,
            definition=definition,
            scope=scope,
            metadata=metadata or {},
        )

        self._tools[name] = wrapper

        # 发布工具注册事件
        if self.event_bus:
            from loom.runtime import Task

            event = Task(
                action="tool.registered",
                sourceAgent="sandbox_manager",
                parameters={
                    "tool_name": name,
                    "scope": scope.value,
                },
            )
            await self.event_bus.publish(event, wait_result=False)

    def unregister_tool(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            是否成功注销（如果工具不存在返回 False）
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    async def register_mcp_server(self, server_id: str, server: Any) -> list[MCPToolDefinition]:
        """
        注册 MCP 服务器并自动发现工具

        Args:
            server_id: 服务器唯一标识
            server: MCP 服务器实例（实现 MCPServer 接口）

        Returns:
            发现的工具列表

        Raises:
            ValueError: 服务器 ID 已存在
        """
        # 初始化 MCP 适配器（如果尚未初始化）
        if self._mcp_adapter is None:
            self._mcp_adapter = MCPAdapter(event_bus=self.event_bus)

        # 注册服务器（这会自动发现工具）
        await self._mcp_adapter.register_server(server_id, server)

        # 获取发现的工具
        mcp_tools = await self._mcp_adapter.discover_tools(server_id)

        # 为每个 MCP 工具创建包装器
        # 为每个 MCP 工具创建包装器
        for mcp_tool in mcp_tools:
            # 使用工厂函数避免闭包变量捕获问题
            def _create_mcp_func(tool_def: MCPToolDefinition, adapter_inst: MCPAdapter):
                async def _mcp_wrapper(**kwargs: Any) -> Any:
                    return await adapter_inst.call_tool(tool_def.name, kwargs)

                return _mcp_wrapper

            wrapper = ToolWrapper(
                name=mcp_tool.name,
                func=_create_mcp_func(mcp_tool, self._mcp_adapter),
                definition=mcp_tool,
                scope=ToolScope.MCP,
                server_id=server_id,
            )
            self._tools[mcp_tool.name] = wrapper

        return mcp_tools

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        执行工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果

        Raises:
            ValueError: 工具不存在
            Exception: 工具执行失败
        """
        wrapper = self._tools.get(name)
        if not wrapper:
            raise ValueError(f"Tool not found: {name}")

        # 发布工具执行开始事件
        if self.event_bus:
            from loom.runtime import Task

            event = Task(
                action="tool.executing",
                sourceAgent="sandbox_manager",
                parameters={
                    "tool_name": name,
                    "scope": wrapper.scope.value,
                },
            )
            await self.event_bus.publish(event, wait_result=False)

        # 根据作用域执行工具
        try:
            if wrapper.scope == ToolScope.SANDBOXED:
                result = await wrapper.execute(arguments, sandbox=self.sandbox)
            elif wrapper.scope == ToolScope.MCP:
                # MCP 工具通过适配器执行
                result = await wrapper.execute(arguments)
            else:
                # SYSTEM 和 CONTEXT 工具直接执行
                result = await wrapper.execute(arguments)

            # 发布工具执行成功事件
            if self.event_bus:
                from loom.runtime import Task

                event = Task(
                    action="tool.completed",
                    sourceAgent="sandbox_manager",
                    parameters={
                        "tool_name": name,
                        "success": True,
                    },
                )
                await self.event_bus.publish(event, wait_result=False)

            return result

        except Exception as e:
            # 发布工具执行失败事件
            if self.event_bus:
                from loom.runtime import Task

                event = Task(
                    action="tool.completed",
                    sourceAgent="sandbox_manager",
                    parameters={
                        "tool_name": name,
                        "success": False,
                        "error": str(e),
                    },
                )
                await self.event_bus.publish(event, wait_result=False)

            raise

    def get_tool(self, name: str) -> ToolWrapper | None:
        """
        获取工具包装器

        Args:
            name: 工具名称

        Returns:
            工具包装器，如果不存在返回 None
        """
        return self._tools.get(name)

    def list_tools(self) -> list[MCPToolDefinition]:
        """
        列出所有已注册的工具定义

        Returns:
            工具定义列表（MCP 格式）
        """
        return [wrapper.definition for wrapper in self._tools.values()]

    def list_tool_names(self) -> list[str]:
        """
        列出所有已注册的工具名称

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def get_tools_by_scope(self, scope: ToolScope) -> list[ToolWrapper]:
        """
        按作用域获取工具

        Args:
            scope: 工具作用域

        Returns:
            该作用域下的所有工具
        """
        return [wrapper for wrapper in self._tools.values() if wrapper.scope == scope]

    @property
    def mcp_adapter(self) -> MCPAdapter | None:
        """获取 MCP 适配器"""
        return self._mcp_adapter

    def __len__(self) -> int:
        """返回已注册工具的数量"""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """检查工具是否已注册"""
        return name in self._tools
