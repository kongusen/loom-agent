from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field, create_model

from loom.interfaces.tool import BaseTool
from .client import MCPClient


class MCPTool(BaseTool):
    """MCP 工具适配为 Loom 工具。"""

    def __init__(self, mcp_tool_spec: Dict, mcp_client: MCPClient) -> None:
        self.mcp_spec = mcp_tool_spec
        self.mcp_client = mcp_client
        self.name = mcp_tool_spec["name"]
        self.description = mcp_tool_spec.get("description", "")
        self.args_schema = self._build_pydantic_schema(mcp_tool_spec.get("inputSchema", {}))

    def _build_pydantic_schema(self, json_schema: Dict) -> type[BaseModel]:
        properties = json_schema.get("properties", {})
        required = set(json_schema.get("required", []))
        fields: Dict[str, tuple[type, Any]] = {}
        for fname, spec in properties.items():
            py_type = self._json_type_to_python(spec.get("type", "string"))
            desc = spec.get("description", "")
            default = ... if fname in required else spec.get("default", None)
            fields[fname] = (py_type, Field(default, description=desc))
        return create_model(f"{self.name.title()}Args", **fields)  # type: ignore[arg-type]

    def _json_type_to_python(self, json_type: str) -> type:
        return {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }.get(json_type, str)

    async def run(self, **kwargs) -> Any:
        result = await self.mcp_client.call_tool(self.name, kwargs)
        content = result.get("content", [])
        if isinstance(content, list) and content:
            return content[0].get("text", "")
        return result

