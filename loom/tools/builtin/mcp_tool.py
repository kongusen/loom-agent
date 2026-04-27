"""MCP 工具定义"""

from ..schema import Tool, ToolDefinition, ToolParameter
from .mcp_operations import mcp_call_tool, mcp_list_resources, mcp_read_resource

MCP_LIST_TOOL = Tool(
    definition=ToolDefinition(
        name="ListMcpResources",
        description="列出 MCP 资源",
        parameters=[ToolParameter("server", "string", "服务器名", required=False)],
        is_read_only=True,
    ),
    handler=mcp_list_resources,
)

MCP_READ_TOOL = Tool(
    definition=ToolDefinition(
        name="ReadMcpResource",
        description="读取 MCP 资源",
        parameters=[
            ToolParameter("server", "string", "服务器名"),
            ToolParameter("uri", "string", "资源 URI"),
        ],
        is_read_only=True,
    ),
    handler=mcp_read_resource,
)

MCP_CALL_TOOL = Tool(
    definition=ToolDefinition(
        name="MCPTool",
        description="调用 MCP 工具",
        parameters=[
            ToolParameter("server", "string", "服务器名"),
            ToolParameter("tool_name", "string", "工具名"),
            ToolParameter("arguments", "object", "参数"),
        ],
    ),
    handler=mcp_call_tool,
)
