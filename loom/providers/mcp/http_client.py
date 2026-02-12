"""
MCP HTTP Client - 基于 HTTP 的 MCP 客户端

通过 HTTP 请求与 MCP 服务器通信。

特性：
1. HTTP 传输 - 通过 HTTP POST 进行 JSON-RPC 通信
2. 异步支持 - 使用 httpx 进行异步请求
3. 连接池 - 复用 HTTP 连接
4. 超时控制 - 请求超时管理
"""

from typing import Any

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from loom.api import __version__
from loom.providers.mcp.interface import MCPProvider
from loom.tools.mcp_types import MCPPrompt, MCPResource, MCPToolDefinition, MCPToolResult


class HttpMCPClient(MCPProvider):
    """
    基于 HTTP 的 MCP 客户端

    通过 HTTP POST 请求与 MCP 服务器通信。
    """

    def __init__(
        self,
        provider_id: str,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        """
        初始化 HTTP MCP 客户端

        Args:
            provider_id: 提供者唯一标识
            base_url: MCP 服务器基础 URL
            headers: 自定义请求头
            timeout: 请求超时时间
        """
        super().__init__(provider_id)

        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for HTTP MCP client. Install it with: pip install httpx"
            )

        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._request_id = 0

    async def connect(self) -> None:
        """连接到 MCP 服务器（创建 HTTP 客户端）"""
        if self._connected:
            return

        try:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            )

            # 发送初始化请求
            await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "loom-agent",
                        "version": __version__,
                    },
                },
            )

            self._connected = True

        except Exception as e:
            raise ConnectionError(f"Failed to connect to MCP server: {str(e)}") from e

    async def disconnect(self) -> None:
        """断开连接（关闭 HTTP 客户端）"""
        if not self._connected or not self._client:
            return

        try:
            await self._client.aclose()
        finally:
            self._connected = False
            self._client = None

    async def list_tools(self) -> list[MCPToolDefinition]:
        """列出所有可用工具"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        response = await self._send_request("tools/list", {})
        tools_data = response.get("tools", [])

        return [
            MCPToolDefinition(
                name=tool["name"],
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {}),
            )
            for tool in tools_data
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """调用指定工具"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        response = await self._send_request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
        )

        return MCPToolResult(
            content=response.get("content", []),
            is_error=response.get("isError", False),
        )

    async def list_resources(self) -> list[MCPResource]:
        """列出所有可用资源"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        response = await self._send_request("resources/list", {})
        resources_data = response.get("resources", [])

        return [
            MCPResource(
                uri=res["uri"],
                name=res["name"],
                mime_type=res.get("mimeType", "text/plain"),
                description=res.get("description"),
            )
            for res in resources_data
        ]

    async def read_resource(self, uri: str) -> str:
        """读取资源内容"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        response = await self._send_request("resources/read", {"uri": uri})
        contents = response.get("contents", [])

        if not contents or not isinstance(contents, list):
            return ""

        first_content = contents[0] if contents else {}
        if isinstance(first_content, dict):
            text = first_content.get("text", "")
            return str(text) if text is not None else ""
        return ""

    async def list_prompts(self) -> list[MCPPrompt]:
        """列出所有可用提示模板"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        response = await self._send_request("prompts/list", {})
        prompts_data = response.get("prompts", [])

        return [
            MCPPrompt(
                name=prompt["name"],
                description=prompt.get("description", ""),
                arguments=prompt.get("arguments", []),
            )
            for prompt in prompts_data
        ]

    async def get_prompt(self, name: str, arguments: dict[str, Any]) -> str:
        """获取提示模板内容"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        response = await self._send_request(
            "prompts/get",
            {
                "name": name,
                "arguments": arguments,
            },
        )

        messages = response.get("messages", [])
        if not messages:
            return ""

        return "\n".join(msg.get("content", {}).get("text", "") for msg in messages)

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """发送 JSON-RPC 请求"""
        if not self._client:
            raise RuntimeError("Client not available")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        # 发送 HTTP POST 请求
        response = await self._client.post("/", json=request)
        response.raise_for_status()

        response_data = response.json()

        # 检查错误
        if "error" in response_data:
            error = response_data["error"]
            if isinstance(error, dict):
                error_msg = error.get("message", "Unknown error")
            else:
                error_msg = str(error)
            raise RuntimeError(f"MCP error: {error_msg}")

        result = response_data.get("result", {})
        if not isinstance(result, dict):
            return {}
        return result
