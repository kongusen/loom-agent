"""Shell 和 Web 工具"""

from .shell_operations import bash
from .web_operations import web_fetch, web_search
from ..schema import Tool, ToolDefinition, ToolParameter


BASH_TOOL = Tool(
    definition=ToolDefinition(
        name="Bash",
        description="执行 shell 命令",
        parameters=[
            ToolParameter("command", "string", "命令"),
            ToolParameter("timeout", "integer", "超时(ms)", required=False, default=120000)
        ],
        is_read_only=False
    ),
    handler=bash
)

WEB_FETCH_TOOL = Tool(
    definition=ToolDefinition(
        name="WebFetch",
        description="获取网页内容",
        parameters=[
            ToolParameter("url", "string", "URL"),
            ToolParameter("prompt", "string", "提示")
        ],
        is_read_only=True,
        is_concurrency_safe=True
    ),
    handler=web_fetch
)

WEB_SEARCH_TOOL = Tool(
    definition=ToolDefinition(
        name="WebSearch",
        description="网页搜索",
        parameters=[
            ToolParameter("query", "string", "搜索查询")
        ],
        is_read_only=True,
        is_concurrency_safe=True
    ),
    handler=web_search
)
