"""
Todo Tool - 任务管理工具

提供任务列表管理功能，帮助 Agent 跟踪和组织工作。

特性：
1. 任务状态管理（pending, in_progress, completed）
2. 持久化存储（JSON 文件）
3. 任务查询和更新

任务存储在沙箱内的 .todos.json 文件中。
"""

import json
from typing import Any

from loom.protocol.mcp import MCPToolDefinition
from loom.tools.core.sandbox import Sandbox

# Optional import for SandboxToolManager
try:
    from loom.tools.core.sandbox_manager import SandboxToolManager, ToolScope
except ImportError:
    SandboxToolManager = None  # type: ignore
    ToolScope = None  # type: ignore


class TodoTool:
    """
    任务管理工具

    管理任务列表，支持增删改查。
    """

    def __init__(self, sandbox: Sandbox, storage_file: str = ".todos.json"):
        """
        初始化 Todo 工具

        Args:
            sandbox: 沙箱实例
            storage_file: 任务存储文件名
        """
        self.sandbox = sandbox
        self.storage_file = storage_file
        self.storage_path = sandbox.root_dir / storage_file

    def _load_todos(self) -> list[dict[str, Any]]:
        """加载任务列表"""
        if not self.storage_path.exists():
            return []

        try:
            content = self.storage_path.read_text(encoding="utf-8")
            data = json.loads(content)
            # 类型转换：确保返回 list[dict[str, Any]]
            if isinstance(data, list):
                return data  # type: ignore[return-value]
            return []
        except (json.JSONDecodeError, Exception):
            return []

    def _save_todos(self, todos: list[dict[str, Any]]) -> None:
        """保存任务列表"""
        content = json.dumps(todos, indent=2, ensure_ascii=False)
        self.storage_path.write_text(content, encoding="utf-8")

    async def write_todos(self, todos: list[dict[str, str]]) -> dict[str, str]:
        """
        写入任务列表（覆盖）

        Args:
            todos: 任务列表，每个任务包含：
                - content: 任务内容
                - status: 状态（pending, in_progress, completed）
                - activeForm: 进行时形式

        Returns:
            结果字典
        """
        try:
            # 验证任务格式
            for todo in todos:
                if "content" not in todo or "status" not in todo:
                    return {
                        "success": "false",
                        "error": "Each todo must have 'content' and 'status' fields",
                    }

                if todo["status"] not in ["pending", "in_progress", "completed"]:
                    return {
                        "success": "false",
                        "error": f"Invalid status: {todo['status']}",
                    }

            # 保存任务
            self._save_todos(todos)

            return {
                "success": "true",
                "message": f"Saved {len(todos)} todos",
                "count": str(len(todos)),
            }
        except Exception as e:
            return {
                "success": "false",
                "error": f"Failed to write todos: {str(e)}",
            }

    async def read_todos(self) -> dict[str, Any]:
        """
        读取任务列表

        Returns:
            结果字典，包含任务列表
        """
        try:
            todos = self._load_todos()
            return {
                "success": "true",
                "todos": todos,
                "count": str(len(todos)),
            }
        except Exception as e:
            return {
                "success": "false",
                "error": f"Failed to read todos: {str(e)}",
                "todos": [],
            }


def create_todo_tool(sandbox: Sandbox) -> dict:
    """
    创建 Todo 工具定义

    Args:
        sandbox: 沙箱实例

    Returns:
        OpenAI 格式的工具定义
    """
    tool = TodoTool(sandbox)

    return {
        "type": "function",
        "function": {
            "name": "todo_write",
            "description": f"Manage task list in the sandbox ({sandbox.root_dir}). "
            "Write or update the complete todo list. Each todo must have 'content', 'status', and 'activeForm' fields. "
            "Status must be one of: pending, in_progress, completed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "description": "Complete list of todos",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "Task description",
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                    "description": "Task status",
                                },
                                "activeForm": {
                                    "type": "string",
                                    "description": "Present continuous form of the task",
                                },
                            },
                            "required": ["content", "status", "activeForm"],
                        },
                    },
                },
                "required": ["todos"],
            },
        },
        "_executor": tool.write_todos,
    }


async def register_todo_tool_to_manager(
    manager: "SandboxToolManager",
) -> None:
    """
    注册 Todo 工具到沙盒工具管理器

    这是新的推荐方式，通过 SandboxToolManager 管理所有工具。

    Args:
        manager: 沙盒工具管理器实例

    Example:
        manager = SandboxToolManager(sandbox)
        await register_todo_tool_to_manager(manager)
        # 工具已注册，可以通过 manager.execute_tool() 调用
    """
    if SandboxToolManager is None or ToolScope is None:
        raise ImportError("SandboxToolManager is not available")

    tool = TodoTool(manager.sandbox)

    # 注册 todo_write 工具
    todo_definition = MCPToolDefinition(
        name="todo_write",
        description=f"Manage task list in the sandbox ({manager.sandbox.root_dir}). "
        "Write or update the complete todo list. Each todo must have 'content', 'status', and 'activeForm' fields. "
        "Status must be one of: pending, in_progress, completed.",
        input_schema={
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "Complete list of todos",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Task description",
                            },
                            "status": {
                                "type": "string",
                                "description": "Task status",
                            },
                            "activeForm": {
                                "type": "string",
                                "description": "Present continuous form of the task",
                            },
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                },
            },
            "required": ["todos"],
        },
    )
    await manager.register_tool(
        "todo_write",
        tool.write_todos,
        todo_definition,
        ToolScope.SANDBOXED,
    )
