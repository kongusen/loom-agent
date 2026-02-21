"""
Model Context Protocol (MCP) - MCP 协议数据类型

MCP 协议提供：
- Tools: 工具定义和调用
- Resources: 资源访问
- Prompts: 提示模板
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MCPToolDefinition(BaseModel):
    """MCP 工具定义"""

    name: str
    description: str
    input_schema: dict[str, Any] = Field(..., alias="inputSchema")

    model_config = ConfigDict(populate_by_name=True)


class MCPResource(BaseModel):
    """MCP 资源定义"""

    uri: str
    name: str
    mime_type: str = Field(..., alias="mimeType")
    description: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class MCPPrompt(BaseModel):
    """MCP 提示模板定义"""

    name: str
    description: str
    arguments: list[dict[str, Any]] = Field(default_factory=list)


class MCPToolCall(BaseModel):
    """MCP 工具调用请求"""

    name: str
    arguments: dict[str, Any]


class MCPToolResult(BaseModel):
    """MCP 工具调用结果"""

    content: list[dict[str, Any]]
    is_error: bool = False


class MCPServer(ABC):
    """MCP 服务器抽象接口"""

    @abstractmethod
    async def list_tools(self) -> list[MCPToolDefinition]:
        """列出可用工具"""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """调用指定工具"""
        pass

    @abstractmethod
    async def list_resources(self) -> list[MCPResource]:
        """列出可用资源"""
        pass

    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """读取资源内容"""
        pass

    @abstractmethod
    async def list_prompts(self) -> list[MCPPrompt]:
        """列出可用提示模板"""
        pass

    @abstractmethod
    async def get_prompt(self, name: str, arguments: dict[str, Any]) -> str:
        """获取提示内容"""
        pass
