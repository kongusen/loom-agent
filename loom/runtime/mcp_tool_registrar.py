"""MCP tool registration helpers for AgentEngine wiring."""

from __future__ import annotations

from typing import Any

from ..tools.schema import Tool, ToolDefinition, ToolParameter


class MCPToolRegistrar:
    """Registers connected MCP server tools into a ToolRegistry."""

    def __init__(self, tool_registry: Any) -> None:
        self.tool_registry = tool_registry

    def register(self, ecosystem_manager: Any) -> None:
        bridge = ecosystem_manager.mcp_bridge
        for server_name, server in bridge.servers.items():
            if not server.connected or not server.tools:
                continue
            for tool_spec in server.tools:
                name = tool_spec.get("name", "")
                if not name:
                    continue
                self.tool_registry.register(
                    self._build_tool(
                        bridge=bridge,
                        server_name=server_name,
                        tool_name=name,
                        tool_spec=tool_spec,
                    )
                )

    def _build_tool(
        self,
        *,
        bridge: Any,
        server_name: str,
        tool_name: str,
        tool_spec: dict[str, Any],
    ) -> Tool:
        scoped_name = f"mcp__{server_name}__{tool_name}".replace(":", "__")
        input_schema = tool_spec.get("inputSchema") or tool_spec.get("parameters") or {}
        props = input_schema.get("properties", {})
        required_set = set(input_schema.get("required", []))
        parameters = [
            ToolParameter(
                name=param_name,
                type=param_info.get("type", "string"),
                description=param_info.get("description", ""),
                required=param_name in required_set,
            )
            for param_name, param_info in props.items()
        ]

        async def _handler(_sn=server_name, _tn=tool_name, **kwargs: Any) -> Any:
            return bridge.execute_tool(_sn, _tn, **kwargs)

        return Tool(
            definition=ToolDefinition(
                name=scoped_name,
                description=tool_spec.get("description", ""),
                parameters=parameters,
                is_read_only=_mcp_tool_bool(
                    tool_spec,
                    "is_read_only",
                    "readOnly",
                    "readOnlyHint",
                ),
                is_destructive=_mcp_tool_bool(
                    tool_spec,
                    "is_destructive",
                    "destructive",
                    "destructiveHint",
                ),
                is_concurrency_safe=_mcp_tool_bool(
                    tool_spec,
                    "is_concurrency_safe",
                    "concurrencySafe",
                    "concurrencySafeHint",
                ),
            ),
            handler=_handler,
        )


def _mcp_tool_bool(
    tool_spec: dict[str, Any],
    direct_key: str,
    camel_key: str,
    annotation_key: str,
) -> bool:
    """Read common MCP tool metadata boolean shapes."""
    annotations = tool_spec.get("annotations")
    if not isinstance(annotations, dict):
        annotations = {}
    for value in (
        tool_spec.get(direct_key),
        tool_spec.get(camel_key),
        annotations.get(annotation_key),
    ):
        if value is not None:
            return bool(value)
    return False
