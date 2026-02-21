"""
MCP Provider Interface - MCP 提供者接口

定义 MCP 提供者的统一接口，用于连接和管理 MCP 服务器。

MCP Provider 负责：
1. 连接管理 - 建立和维护与 MCP 服务器的连接
2. 工具发现 - 发现和加载 MCP 服务器提供的工具
3. 工具调用 - 执行 MCP 工具
4. 资源访问 - 访问 MCP 资源
5. 生命周期管理 - 连接、断开、重连
"""

from abc import ABC, abstractmethod
from typing import Any

from loom.tools.mcp_types import MCPPrompt, MCPResource, MCPToolDefinition, MCPToolResult


class MCPProvider(ABC):
    """
    MCP 提供者抽象接口

    所有 MCP 客户端实现都应该继承此接口。
    """

    def __init__(self, provider_id: str):
        """
        初始化 MCP 提供者

        Args:
            provider_id: 提供者唯一标识
        """
        self.provider_id = provider_id
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """
        连接到 MCP 服务器

        Raises:
            ConnectionError: 如果连接失败
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        断开与 MCP 服务器的连接
        """
        pass

    @abstractmethod
    async def list_tools(self) -> list[MCPToolDefinition]:
        """
        列出所有可用工具

        Returns:
            工具定义列表

        Raises:
            RuntimeError: 如果未连接
        """
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """
        调用指定工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果

        Raises:
            RuntimeError: 如果未连接
            ValueError: 如果工具不存在
        """
        pass

    @abstractmethod
    async def list_resources(self) -> list[MCPResource]:
        """
        列出所有可用资源

        Returns:
            资源定义列表

        Raises:
            RuntimeError: 如果未连接
        """
        pass

    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """
        读取资源内容

        Args:
            uri: 资源 URI

        Returns:
            资源内容

        Raises:
            RuntimeError: 如果未连接
            ValueError: 如果资源不存在
        """
        pass

    @abstractmethod
    async def list_prompts(self) -> list[MCPPrompt]:
        """
        列出所有可用提示模板

        Returns:
            提示模板列表

        Raises:
            RuntimeError: 如果未连接
        """
        pass

    @abstractmethod
    async def get_prompt(self, name: str, arguments: dict[str, Any]) -> str:
        """
        获取提示模板内容

        Args:
            name: 模板名称
            arguments: 模板参数

        Returns:
            渲染后的提示内容

        Raises:
            RuntimeError: 如果未连接
            ValueError: 如果模板不存在
        """
        pass

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.disconnect()
