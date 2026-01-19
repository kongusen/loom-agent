"""
MCP Stdio Client - 基于 stdio 的 MCP 客户端

通过标准输入输出与 MCP 服务器通信。

特性：
1. 进程管理 - 启动和管理 MCP 服务器进程
2. JSON-RPC 通信 - 通过 stdin/stdout 进行通信
3. 异步支持 - 完全异步的实现
4. 错误处理 - 完善的错误处理和重试机制
"""

import asyncio
import json
from typing import Any

from loom.api import __version__
from loom.protocol.mcp import MCPPrompt, MCPResource, MCPToolDefinition, MCPToolResult
from loom.providers.mcp.interface import MCPProvider


class StdioMCPClient(MCPProvider):
    """
    基于 stdio 的 MCP 客户端

    通过 subprocess 启动 MCP 服务器，并通过 stdin/stdout 进行通信。
    """

    def __init__(
        self,
        provider_id: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ):
        """
        初始化 stdio MCP 客户端

        Args:
            provider_id: 提供者唯一标识
            command: MCP 服务器命令
            args: 命令参数
            env: 环境变量
        """
        super().__init__(provider_id)
        self.command = command
        self.args = args or []
        self.env = env
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def connect(self) -> None:
        """连接到 MCP 服务器（启动进程）"""
        if self._connected:
            return

        try:
            # 启动 MCP 服务器进程
            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )

            self._connected = True

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

        except Exception as e:
            raise ConnectionError(f"Failed to start MCP server: {str(e)}") from e

    async def disconnect(self) -> None:
        """断开连接（终止进程）"""
        if not self._connected or not self._process:
            return

        try:
            # 发送关闭通知
            await self._send_notification("notifications/cancelled", {})

            # 终止进程
            self._process.terminate()
            await self._process.wait()

        except Exception:
            # 强制杀死进程
            if self._process:
                self._process.kill()
                await self._process.wait()

        finally:
            self._connected = False
            self._process = None

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

        if not contents:
            return ""

        # 返回第一个内容项的文本
        first_content = contents[0]
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

        # 合并所有消息内容
        return "\n".join(msg.get("content", {}).get("text", "") for msg in messages)

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """发送 JSON-RPC 请求"""
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise RuntimeError("Process not available")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        # 发送请求
        request_line = json.dumps(request) + "\n"
        self._process.stdin.write(request_line.encode("utf-8"))
        await self._process.stdin.drain()

        # 读取响应
        response_line = await self._process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")

        response = json.loads(response_line.decode("utf-8"))

        # 检查错误
        if "error" in response:
            error = response["error"]
            if isinstance(error, dict):
                error_msg = error.get("message", "Unknown error")
            else:
                error_msg = str(error)
            raise RuntimeError(f"MCP error: {error_msg}")

        result = response.get("result", {})
        if not isinstance(result, dict):
            return {}
        return result

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """发送 JSON-RPC 通知（不需要响应）"""
        if not self._process or not self._process.stdin:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        notification_line = json.dumps(notification) + "\n"
        self._process.stdin.write(notification_line.encode("utf-8"))
        await self._process.stdin.drain()
