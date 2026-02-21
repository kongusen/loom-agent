"""
MCP Adapter - MCP 协议适配器

基于公理A1（统一接口公理）和A6（四范式工作公理）：
实现 MCP 协议的客户端适配器，将 MCP 工具集成到 Loom 工具系统。

功能：
- 注册 MCP 服务器
- 发现和注册 MCP 工具
- 调用 MCP 工具
- 格式转换（MCP ↔ Loom）

设计原则：
1. 无缝集成 - 与现有工具系统兼容
2. 异步优先 - 所有操作都是异步的
3. 错误处理 - 完善的错误处理机制
"""

from typing import Any

from loom.events import EventBus
from loom.tools.mcp_types import MCPServer, MCPToolDefinition


class MCPAdapter:
    """
    MCP 协议适配器

    将 MCP 服务器的工具集成到 Loom 工具系统。
    """

    def __init__(self, event_bus: EventBus | None = None):
        """
        初始化 MCP 适配器

        Args:
            event_bus: 事件总线（可选）
        """
        self.event_bus = event_bus
        self.servers: dict[str, MCPServer] = {}
        self.tools: dict[
            str, tuple[str, MCPToolDefinition]
        ] = {}  # tool_name -> (server_id, tool_def)

    async def register_server(self, server_id: str, server: MCPServer) -> None:
        """
        注册 MCP 服务器

        Args:
            server_id: 服务器唯一标识
            server: MCP 服务器实例
        """
        self.servers[server_id] = server

        # 自动发现工具
        await self.discover_tools(server_id)

    async def discover_tools(self, server_id: str) -> list[MCPToolDefinition]:
        """
        发现 MCP 服务器的工具

        Args:
            server_id: 服务器标识

        Returns:
            发现的工具列表（MCP 格式）
        """
        server = self.servers.get(server_id)
        if not server:
            raise ValueError(f"Server not found: {server_id}")

        # 获取 MCP 工具列表
        mcp_tools = await server.list_tools()

        # 注册工具映射
        for mcp_tool in mcp_tools:
            self.tools[mcp_tool.name] = (server_id, mcp_tool)

        return mcp_tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果

        Raises:
            ValueError: 工具未找到
            Exception: 工具执行失败
        """
        # 查找工具
        tool_info = self.tools.get(tool_name)
        if not tool_info:
            raise ValueError(f"Tool not found: {tool_name}")

        server_id, mcp_tool = tool_info
        server = self.servers.get(server_id)
        if not server:
            raise ValueError(f"Server not found: {server_id}")

        try:
            # 调用 MCP 工具
            result = await server.call_tool(tool_name, arguments)

            # 发送事件（如果有事件总线）
            if self.event_bus:
                from loom.runtime import Task

                event = Task(
                    action="mcp.tool.called",
                    sourceAgent=f"mcp/{server_id}",
                    parameters={
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "success": not result.is_error,
                    },
                )
                await self.event_bus.publish(event, wait_result=False)

            # 处理结果
            if result.is_error:
                raise Exception(f"Tool execution failed: {result.content}")

            return result.content

        except Exception as e:
            # 发送错误事件
            if self.event_bus:
                from loom.runtime import Task

                event = Task(
                    action="mcp.tool.failed",
                    sourceAgent=f"mcp/{server_id}",
                    parameters={
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "error": str(e),
                    },
                )
                await self.event_bus.publish(event, wait_result=False)

            raise

    def list_tools(self) -> list[str]:
        """
        列出所有已注册的工具名称

        Returns:
            工具名称列表
        """
        return list(self.tools.keys())

    def get_tool_definition(self, tool_name: str) -> MCPToolDefinition | None:
        """
        获取工具定义（MCP 格式）

        Args:
            tool_name: 工具名称

        Returns:
            工具定义，如果不存在返回 None
        """
        tool_info = self.tools.get(tool_name)
        if not tool_info:
            return None

        _, mcp_tool = tool_info
        return mcp_tool
