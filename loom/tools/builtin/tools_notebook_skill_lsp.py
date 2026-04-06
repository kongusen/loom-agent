"""Notebook、Skill、LSP 工具定义"""

from .notebook_operations import notebook_edit
from .skill_operations import skill_invoke, skill_discover
from .lsp_operations import lsp_get_diagnostics, lsp_execute_code
from ..schema import Tool, ToolDefinition, ToolParameter


NOTEBOOK_EDIT_TOOL = Tool(
    definition=ToolDefinition(
        name="NotebookEdit",
        description="编辑 Jupyter Notebook",
        parameters=[
            ToolParameter("notebook_path", "string", "Notebook 路径"),
            ToolParameter("cell_id", "string", "单元格 ID"),
            ToolParameter("new_source", "string", "新内容"),
            ToolParameter("cell_type", "string", "单元格类型", required=False, default="code")
        ]
    ),
    handler=notebook_edit
)

SKILL_TOOL = Tool(
    definition=ToolDefinition(
        name="Skill",
        description="调用 Skill",
        parameters=[
            ToolParameter("skill", "string", "Skill 名称"),
            ToolParameter("args", "string", "参数", required=False, default="")
        ]
    ),
    handler=skill_invoke
)

SKILL_DISCOVER_TOOL = Tool(
    definition=ToolDefinition(
        name="DiscoverSkills",
        description="发现可用 Skills",
        parameters=[],
        is_read_only=True
    ),
    handler=skill_discover
)

LSP_DIAGNOSTICS_TOOL = Tool(
    definition=ToolDefinition(
        name="GetDiagnostics",
        description="获取语言诊断",
        parameters=[
            ToolParameter("uri", "string", "文件 URI", required=False)
        ],
        is_read_only=True
    ),
    handler=lsp_get_diagnostics
)

LSP_EXECUTE_TOOL = Tool(
    definition=ToolDefinition(
        name="ExecuteCode",
        description="执行代码",
        parameters=[
            ToolParameter("code", "string", "代码")
        ]
    ),
    handler=lsp_execute_code
)
