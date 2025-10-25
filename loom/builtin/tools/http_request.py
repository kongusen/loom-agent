"""HTTP 请求工具 - 发送 HTTP 请求"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


class HTTPRequestInput(BaseModel):
    """HTTP 请求输入参数"""

    url: str = Field(description="URL to request")
    method: str = Field(default="GET", description="HTTP method (GET, POST, PUT, DELETE)")
    headers: Optional[dict] = Field(default=None, description="Request headers")
    body: Optional[str] = Field(default=None, description="Request body (for POST/PUT)")


class HTTPRequestTool(BaseTool):
    """
    HTTP 请求工具 - 发送 HTTP 请求并返回响应

    需要安装: pip install httpx
    """

    name = "http_request"
    description = "Send HTTP requests (GET, POST, PUT, DELETE) to a URL and return the response"
    args_schema = HTTPRequestInput
    is_concurrency_safe = True

    # 🆕 Loom 2.0 - Orchestration attributes
    is_read_only = False  # POST/PUT/DELETE may modify remote state
    category = "network"  # Network operation
    requires_confirmation = False  # Usually safe, but depends on usage

    def __init__(self, timeout: int = 10) -> None:
        if httpx is None:
            raise ImportError("Please install httpx: pip install httpx")
        self.timeout = timeout

    async def run(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        body: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """执行 HTTP 请求"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_kwargs: dict = {"method": method.upper(), "url": url}

                if headers:
                    request_kwargs["headers"] = headers

                if body and method.upper() in ["POST", "PUT", "PATCH"]:
                    request_kwargs["content"] = body

                response = await client.request(**request_kwargs)

                # 格式化响应
                result_lines = [
                    f"HTTP {response.status_code}",
                    f"URL: {url}",
                    f"Method: {method.upper()}",
                    "",
                    "Headers:",
                ]

                for key, value in response.headers.items():
                    result_lines.append(f"  {key}: {value}")

                result_lines.append("")
                result_lines.append("Body:")
                result_lines.append(response.text[:1000])  # 限制输出长度

                if len(response.text) > 1000:
                    result_lines.append(f"\n... (truncated, total {len(response.text)} characters)")

                return "\n".join(result_lines)

        except Exception as e:
            return f"HTTP request error: {type(e).__name__}: {str(e)}"
