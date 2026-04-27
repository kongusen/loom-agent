"""所有工具的统一导出"""

from .agent_task_tool import (
    ASK_USER_TOOL,
    TASK_CREATE_TOOL,
    TASK_GET_TOOL,
    TASK_LIST_TOOL,
    TASK_OUTPUT_TOOL,
    TASK_STOP_TOOL,
    TASK_TOOL,
    TASK_UPDATE_TOOL,
)
from .file_tool import EDIT_TOOL, GLOB_TOOL, GREP_TOOL, READ_TOOL, WRITE_TOOL
from .mcp_tool import MCP_CALL_TOOL, MCP_LIST_TOOL, MCP_READ_TOOL
from .notebook_skill_lsp_tool import (
    LSP_DIAGNOSTICS_TOOL,
    LSP_EXECUTE_TOOL,
    NOTEBOOK_EDIT_TOOL,
    SKILL_DISCOVER_TOOL,
    SKILL_TOOL,
)
from .shell_web_tool import BASH_TOOL, WEB_FETCH_TOOL, WEB_SEARCH_TOOL
from .workflow_config_tool import (
    CONFIG_GET_TOOL,
    CONFIG_SET_TOOL,
    ENTER_PLAN_TOOL,
    ENTER_WORKTREE_TOOL,
    EXIT_PLAN_TOOL,
    EXIT_WORKTREE_TOOL,
    REMOTE_TRIGGER_TOOL,
    SEND_MESSAGE_TOOL,
    SLEEP_TOOL,
    TEAM_CREATE_TOOL,
    TEAM_DELETE_TOOL,
    TODO_WRITE_TOOL,
    TOOL_SEARCH_TOOL,
)

BUILTIN_TOOLS = [
    # 文件 (5)
    READ_TOOL,
    WRITE_TOOL,
    EDIT_TOOL,
    GLOB_TOOL,
    GREP_TOOL,
    # Shell & Web (3)
    BASH_TOOL,
    WEB_FETCH_TOOL,
    WEB_SEARCH_TOOL,
    # Agent & Task (8)
    TASK_TOOL,
    ASK_USER_TOOL,
    TASK_CREATE_TOOL,
    TASK_UPDATE_TOOL,
    TASK_LIST_TOOL,
    TASK_GET_TOOL,
    TASK_OUTPUT_TOOL,
    TASK_STOP_TOOL,
    # MCP (3)
    MCP_LIST_TOOL,
    MCP_READ_TOOL,
    MCP_CALL_TOOL,
    # Notebook, Skill, LSP (5)
    NOTEBOOK_EDIT_TOOL,
    SKILL_TOOL,
    SKILL_DISCOVER_TOOL,
    LSP_DIAGNOSTICS_TOOL,
    LSP_EXECUTE_TOOL,
    # Workflow (4)
    ENTER_PLAN_TOOL,
    EXIT_PLAN_TOOL,
    ENTER_WORKTREE_TOOL,
    EXIT_WORKTREE_TOOL,
    # Config (3)
    CONFIG_GET_TOOL,
    CONFIG_SET_TOOL,
    TOOL_SEARCH_TOOL,
    # Misc (3)
    SLEEP_TOOL,
    SEND_MESSAGE_TOOL,
    TODO_WRITE_TOOL,
    # Team (3)
    TEAM_CREATE_TOOL,
    TEAM_DELETE_TOOL,
    REMOTE_TRIGGER_TOOL,
]


def register_all_tools():
    """注册所有工具到全局注册表"""
    from .registry import get_registry

    registry = get_registry()
    for tool in BUILTIN_TOOLS:
        registry.register(tool)


__all__ = ["BUILTIN_TOOLS", "register_all_tools"]
