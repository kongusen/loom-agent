"""
HTTP Tool - HTTP 请求工具

提供 HTTP 请求功能，支持常见的 HTTP 方法。

特性：
1. 支持 GET, POST, PUT, DELETE 等方法
2. 支持自定义请求头和请求体
3. 超时控制
4. 返回完整的响应信息

注意：此工具不受沙箱限制，可以访问任何 URL。
"""

import json
from typing import Any

from loom.protocol.mcp import MCPToolDefinition

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Optional import for SandboxToolManager
try:
    from loom.tools.sandbox_manager import SandboxToolManager, ToolScope
except ImportError:
    SandboxToolManager = None  # type: ignore
    ToolScope = None  # type: ignore


class HTTPTool:
    """
    HTTP 请求工具

    使用 httpx 进行异步 HTTP 请求。
    """

    def __init__(self, timeout: float = 30.0):
        """
        初始化 HTTP 工具

        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout

    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            url: 请求 URL
            method: HTTP 方法（GET, POST, PUT, DELETE 等）
            headers: 请求头（可选）
            body: 请求体（可选，JSON 字符串）
            timeout: 超时时间（可选）

        Returns:
            结果字典，包含：
            - status_code: 状态码
            - headers: 响应头
            - body: 响应体
            - success: 是否成功
            - error: 错误信息（如果失败）
        """
        if not HTTPX_AVAILABLE:
            return {
                "success": "false",
                "error": "httpx library is not installed. Install it with: pip install httpx",
            }

        try:
            request_timeout = timeout or self.timeout

            async with httpx.AsyncClient(timeout=request_timeout) as client:
                # 准备请求参数
                kwargs: dict[str, Any] = {
                    "method": method.upper(),
                    "url": url,
                }

                if headers:
                    kwargs["headers"] = headers

                if body:
                    # 尝试解析为 JSON
                    try:
                        kwargs["json"] = json.loads(body)
                    except json.JSONDecodeError:
                        # 如果不是 JSON，作为文本发送
                        kwargs["content"] = body

                # 发送请求
                response = await client.request(**kwargs)

                # 返回响应
                return {
                    "status_code": str(response.status_code),
                    "headers": dict(response.headers),
                    "body": response.text,
                    "success": "true" if response.status_code < 400 else "false",
                }

        except httpx.TimeoutException:
            return {
                "success": "false",
                "error": f"Request timed out after {request_timeout} seconds",
            }
        except Exception as e:
            return {
                "success": "false",
                "error": f"HTTP request error: {str(e)}",
            }


def create_http_tool(timeout: float = 30.0) -> dict:
    """
    创建 HTTP 工具定义

    Args:
        timeout: 超时时间

    Returns:
        OpenAI 格式的工具定义
    """
    tool = HTTPTool(timeout)

    return {
        "type": "function",
        "function": {
            "name": "http_request",
            "description": f"Send HTTP requests to external APIs or websites. "
            f"Supports GET, POST, PUT, DELETE methods. Timeout: {timeout}s.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to send the request to",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "description": "HTTP method (default: GET)",
                        "default": "GET",
                    },
                    "headers": {
                        "type": "object",
                        "description": "Request headers (optional)",
                    },
                    "body": {
                        "type": "string",
                        "description": "Request body (optional, JSON string or text)",
                    },
                },
                "required": ["url"],
            },
        },
        "_executor": tool.request,
    }


async def register_http_tool_to_manager(
    manager: "SandboxToolManager",
    timeout: float = 30.0,
) -> None:
    """
    注册 HTTP 工具到沙盒工具管理器

    HTTP 是系统级工具，不受文件系统沙盒约束，可以访问任何 URL。

    Args:
        manager: 沙盒工具管理器实例
        timeout: 请求超时时间（秒）

    Example:
        manager = SandboxToolManager(sandbox)
        await register_http_tool_to_manager(manager)
        # 工具已注册，可以通过 manager.execute_tool() 调用
    """
    if SandboxToolManager is None or ToolScope is None:
        raise ImportError("SandboxToolManager is not available")

    tool = HTTPTool(timeout)

    # 注册 http_request 工具（SYSTEM 作用域 - 不受文件系统沙盒约束）
    http_definition = MCPToolDefinition(
        name="http_request",
        description=f"Send HTTP requests to external APIs or websites. "
        f"Supports GET, POST, PUT, DELETE methods. Timeout: {timeout}s.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to send the request to",
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method (default: GET)",
                },
                "headers": {
                    "type": "object",
                    "description": "Request headers (optional)",
                },
                "body": {
                    "type": "string",
                    "description": "Request body (optional, JSON string or text)",
                },
            },
            "required": ["url"],
        },
    )
    await manager.register_tool(
        "http_request",
        tool.request,
        http_definition,
        ToolScope.SYSTEM,  # HTTP 是系统级操作，不受文件系统沙盒约束
    )
