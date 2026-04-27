"""Agent 和任务工具"""

from ..schema import Tool, ToolDefinition, ToolParameter
from .agent_operations import ask_user, spawn_agent
from .misc_operations import task_output, task_stop
from .task_operations import task_create, task_get, task_list, task_update

TASK_TOOL = Tool(
    definition=ToolDefinition(
        name="Task",
        description="生成子 Agent",
        parameters=[
            ToolParameter("task", "string", "任务描述"),
            ToolParameter("depth", "integer", "深度", required=False, default=1),
        ],
    ),
    handler=spawn_agent,
)

ASK_USER_TOOL = Tool(
    definition=ToolDefinition(
        name="AskUserQuestion",
        description="询问用户",
        parameters=[
            ToolParameter("question", "string", "问题"),
            ToolParameter("options", "array", "选项"),
        ],
    ),
    handler=ask_user,
)

TASK_CREATE_TOOL = Tool(
    definition=ToolDefinition(
        name="TaskCreate",
        description="创建任务",
        parameters=[
            ToolParameter("subject", "string", "主题"),
            ToolParameter("description", "string", "描述"),
        ],
    ),
    handler=task_create,
)

TASK_UPDATE_TOOL = Tool(
    definition=ToolDefinition(
        name="TaskUpdate",
        description="更新任务",
        parameters=[
            ToolParameter("task_id", "string", "任务ID"),
            ToolParameter("status", "string", "状态"),
        ],
    ),
    handler=task_update,
)

TASK_LIST_TOOL = Tool(
    definition=ToolDefinition(
        name="TaskList", description="列出任务", parameters=[], is_read_only=True
    ),
    handler=task_list,
)

TASK_GET_TOOL = Tool(
    definition=ToolDefinition(
        name="TaskGet",
        description="获取任务",
        parameters=[ToolParameter("task_id", "string", "任务ID")],
        is_read_only=True,
    ),
    handler=task_get,
)

TASK_OUTPUT_TOOL = Tool(
    definition=ToolDefinition(
        name="TaskOutput",
        description="获取任务输出",
        parameters=[
            ToolParameter("task_id", "string", "任务ID"),
            ToolParameter("block", "boolean", "阻塞", required=False, default=True),
        ],
        is_read_only=True,
    ),
    handler=task_output,
)

TASK_STOP_TOOL = Tool(
    definition=ToolDefinition(
        name="TaskStop",
        description="停止任务",
        parameters=[ToolParameter("task_id", "string", "任务ID")],
    ),
    handler=task_stop,
)
