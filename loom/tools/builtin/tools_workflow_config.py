"""工作流和配置工具定义"""

from .workflow_operations import enter_plan_mode, exit_plan_mode, enter_worktree, exit_worktree
from .config_operations import config_get, config_set, tool_search
from .misc_operations import sleep, send_message, todo_write
from .team_operations import team_create, team_delete, remote_trigger
from ..schema import Tool, ToolDefinition, ToolParameter


ENTER_PLAN_TOOL = Tool(
    definition=ToolDefinition(
        name="EnterPlanMode",
        description="进入计划模式",
        parameters=[]
    ),
    handler=enter_plan_mode
)

EXIT_PLAN_TOOL = Tool(
    definition=ToolDefinition(
        name="ExitPlanMode",
        description="退出计划模式",
        parameters=[]
    ),
    handler=exit_plan_mode
)

ENTER_WORKTREE_TOOL = Tool(
    definition=ToolDefinition(
        name="EnterWorktree",
        description="进入 worktree",
        parameters=[
            ToolParameter("name", "string", "worktree 名称", required=False)
        ]
    ),
    handler=enter_worktree
)

EXIT_WORKTREE_TOOL = Tool(
    definition=ToolDefinition(
        name="ExitWorktree",
        description="退出 worktree",
        parameters=[]
    ),
    handler=exit_worktree
)

CONFIG_GET_TOOL = Tool(
    definition=ToolDefinition(
        name="ConfigGet",
        description="获取配置",
        parameters=[
            ToolParameter("key", "string", "配置键")
        ],
        is_read_only=True
    ),
    handler=config_get
)

CONFIG_SET_TOOL = Tool(
    definition=ToolDefinition(
        name="ConfigSet",
        description="设置配置",
        parameters=[
            ToolParameter("key", "string", "配置键"),
            ToolParameter("value", "string", "配置值")
        ]
    ),
    handler=config_set
)

TOOL_SEARCH_TOOL = Tool(
    definition=ToolDefinition(
        name="ToolSearch",
        description="搜索工具",
        parameters=[
            ToolParameter("query", "string", "搜索查询")
        ],
        is_read_only=True
    ),
    handler=tool_search
)

SLEEP_TOOL = Tool(
    definition=ToolDefinition(
        name="Sleep",
        description="休眠",
        parameters=[
            ToolParameter("duration", "integer", "时长(ms)")
        ]
    ),
    handler=sleep
)

SEND_MESSAGE_TOOL = Tool(
    definition=ToolDefinition(
        name="SendMessage",
        description="发送消息",
        parameters=[
            ToolParameter("content", "string", "消息内容")
        ]
    ),
    handler=send_message
)

TODO_WRITE_TOOL = Tool(
    definition=ToolDefinition(
        name="TodoWrite",
        description="写待办事项",
        parameters=[
            ToolParameter("items", "array", "待办列表")
        ]
    ),
    handler=todo_write
)

TEAM_CREATE_TOOL = Tool(
    definition=ToolDefinition(
        name="TeamCreate",
        description="创建团队",
        parameters=[
            ToolParameter("name", "string", "团队名"),
            ToolParameter("members", "array", "成员列表")
        ]
    ),
    handler=team_create
)

TEAM_DELETE_TOOL = Tool(
    definition=ToolDefinition(
        name="TeamDelete",
        description="删除团队",
        parameters=[
            ToolParameter("team_id", "string", "团队ID")
        ],
        is_destructive=True
    ),
    handler=team_delete
)

REMOTE_TRIGGER_TOOL = Tool(
    definition=ToolDefinition(
        name="RemoteTrigger",
        description="远程触发",
        parameters=[
            ToolParameter("event", "string", "事件名"),
            ToolParameter("data", "object", "事件数据")
        ]
    ),
    handler=remote_trigger
)
