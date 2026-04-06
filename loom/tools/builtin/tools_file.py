"""内置工具集合 - 使用正确的 schema"""

from .file_operations import read_file, write_file, edit_file, glob_files, grep_files
from .shell_operations import bash
from .web_operations import web_fetch, web_search
from .agent_operations import spawn_agent, ask_user
from .task_operations import task_create, task_update, task_list, task_get
from .mcp_operations import mcp_list_resources, mcp_read_resource, mcp_call_tool
from .notebook_operations import notebook_edit
from .skill_operations import skill_invoke, skill_discover
from .lsp_operations import lsp_get_diagnostics, lsp_execute_code
from .workflow_operations import enter_plan_mode, exit_plan_mode, enter_worktree, exit_worktree
from .config_operations import config_get, config_set, tool_search
from .misc_operations import task_output, task_stop, sleep, send_message, todo_write
from .team_operations import team_create, team_delete, remote_trigger
from ..schema import Tool, ToolDefinition, ToolParameter


# 文件操作工具
READ_TOOL = Tool(
    definition=ToolDefinition(
        name="Read",
        description="读取文件内容",
        parameters=[
            ToolParameter("file_path", "string", "文件路径"),
            ToolParameter("offset", "integer", "起始行", required=False, default=1),
            ToolParameter("limit", "integer", "读取行数", required=False)
        ],
        is_read_only=True,
        is_concurrency_safe=True
    ),
    handler=read_file
)

WRITE_TOOL = Tool(
    definition=ToolDefinition(
        name="Write",
        description="写入文件",
        parameters=[
            ToolParameter("file_path", "string", "文件路径"),
            ToolParameter("content", "string", "文件内容")
        ],
        is_read_only=False
    ),
    handler=write_file
)

EDIT_TOOL = Tool(
    definition=ToolDefinition(
        name="Edit",
        description="编辑文件",
        parameters=[
            ToolParameter("file_path", "string", "文件路径"),
            ToolParameter("old_string", "string", "要替换的字符串"),
            ToolParameter("new_string", "string", "新字符串"),
            ToolParameter("replace_all", "boolean", "是否替换所有", required=False, default=False)
        ],
        is_read_only=False
    ),
    handler=edit_file
)

GLOB_TOOL = Tool(
    definition=ToolDefinition(
        name="Glob",
        description="文件模式匹配",
        parameters=[
            ToolParameter("pattern", "string", "匹配模式"),
            ToolParameter("path", "string", "搜索路径", required=False, default=".")
        ],
        is_read_only=True,
        is_concurrency_safe=True
    ),
    handler=glob_files
)

GREP_TOOL = Tool(
    definition=ToolDefinition(
        name="Grep",
        description="内容搜索",
        parameters=[
            ToolParameter("pattern", "string", "搜索模式"),
            ToolParameter("path", "string", "搜索路径", required=False, default="."),
            ToolParameter("glob_pattern", "string", "文件过滤", required=False, default="*")
        ],
        is_read_only=True,
        is_concurrency_safe=True
    ),
    handler=grep_files
)
