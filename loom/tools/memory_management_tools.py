"""
Memory Management Tools - LLM主动管理记忆层级

基于"框架提供能力，LLM做决策"的原则，将记忆管理从框架硬编码转换为LLM主动控制。

核心工具：
1. 记忆状态查询 - 让LLM了解当前记忆使用情况
2. 任务提升工具 - 让LLM决定哪些任务应该提升到更高层级
3. 任务摘要工具 - 让LLM决定如何总结任务

使用方式：
    from loom.tools.memory_management_tools import create_memory_management_tools

    agent = Agent(
        tools=[...] + create_memory_management_tools(memory),
    )
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory


# ==================== Memory Status Tools ====================


def create_get_memory_stats_tool() -> dict:
    """
    创建获取记忆统计信息工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "get_memory_stats",
            "description": "Get current memory usage statistics across all layers (L1-L4). Use this to understand memory pressure and decide when to promote or clean up tasks.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }


async def execute_get_memory_stats_tool(_args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行获取记忆统计信息

    Args:
        _args: 工具参数（无参数）
        memory: LoomMemory实例

    Returns:
        记忆统计信息
    """
    return {
        "l1": {
            "current": len(memory._l1_tasks),
            "max": memory.max_l1_size,
            "usage_percent": (len(memory._l1_tasks) / memory.max_l1_size * 100)
            if memory.max_l1_size > 0
            else 0,
            "description": "Recent tasks (circular buffer)",
        },
        "l2": {
            "current": len(memory._l2_tasks),
            "max": memory.max_l2_size,
            "usage_percent": (len(memory._l2_tasks) / memory.max_l2_size * 100)
            if memory.max_l2_size > 0
            else 0,
            "description": "Important tasks (sorted by importance)",
        },
        "l3": {
            "current": len(memory._l3_summaries),
            "max": memory.max_l3_size,
            "usage_percent": (len(memory._l3_summaries) / memory.max_l3_size * 100)
            if memory.max_l3_size > 0
            else 0,
            "description": "Task summaries (compressed)",
        },
        "l4": {
            "enabled": memory.enable_l4_vectorization,
            "description": "Vector storage (semantic search)",
        },
        "task_index_size": len(memory._task_index),
        "fact_index_size": len(memory._fact_index),
    }


# ==================== Task Promotion Tools ====================


def create_promote_task_to_l2_tool() -> dict:
    """
    创建提升任务到L2工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "promote_task_to_l2",
            "description": "Promote a task from L1 to L2 (important tasks). Use this when you identify a task that should be kept in working memory due to its importance or relevance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to promote",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for promoting this task (for logging/debugging)",
                    },
                },
                "required": ["task_id"],
            },
        },
    }


async def execute_promote_task_to_l2_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行提升任务到L2

    Args:
        args: 工具参数 {"task_id": "...", "reason": "..."}
        memory: LoomMemory实例

    Returns:
        执行结果
    """
    task_id = args.get("task_id", "")
    reason = args.get("reason", "LLM decision")

    # 查找任务
    task = memory._task_index.get(task_id)
    if not task:
        return {
            "success": False,
            "error": f"Task {task_id} not found in memory",
        }

    # 检查是否已在L2
    if task_id in [t.task_id for t in memory._l2_tasks]:
        return {
            "success": False,
            "error": f"Task {task_id} is already in L2",
        }

    # 提升到L2
    memory._add_to_l2(task)

    return {
        "success": True,
        "task_id": task_id,
        "reason": reason,
        "l2_size": len(memory._l2_tasks),
    }


# ==================== Task Summary Tools ====================


def create_create_task_summary_tool() -> dict:
    """
    创建任务摘要工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "create_task_summary",
            "description": "Create a summary of a task and store it in L3 (compressed memory). Use this to compress less important tasks to save memory while retaining key information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to summarize",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of the task (what was done and the result)",
                    },
                    "importance": {
                        "type": "number",
                        "description": "Importance score (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorizing the task",
                    },
                },
                "required": ["task_id", "summary"],
            },
        },
    }


async def execute_create_task_summary_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行创建任务摘要

    Args:
        args: 工具参数 {"task_id": "...", "summary": "...", "importance": 0.5, "tags": [...]}
        memory: LoomMemory实例

    Returns:
        执行结果
    """
    from datetime import datetime

    from loom.memory.types import TaskSummary

    task_id = args.get("task_id", "")
    summary_text = args.get("summary", "")
    importance = args.get("importance", 0.5)
    tags = args.get("tags", [])

    # 查找任务
    task = memory._task_index.get(task_id)
    if not task:
        return {
            "success": False,
            "error": f"Task {task_id} not found in memory",
        }

    # 创建摘要
    task_summary = TaskSummary(
        task_id=task.task_id,
        action=task.action,
        param_summary=str(task.parameters)[:100],  # 截断参数
        result_summary=summary_text,
        importance=importance,
        tags=tags,
        created_at=task.created_at or datetime.now(),
    )

    # 添加到L3
    memory._add_to_l3(task_summary)

    return {
        "success": True,
        "task_id": task_id,
        "summary": summary_text,
        "l3_size": len(memory._l3_summaries),
    }


# ==================== Helper Functions ====================


def create_all_memory_management_tools() -> list[dict]:
    """
    创建所有记忆管理工具

    Returns:
        所有工具定义的列表
    """
    return [
        create_get_memory_stats_tool(),
        create_promote_task_to_l2_tool(),
        create_create_task_summary_tool(),
    ]


class MemoryManagementToolExecutor:
    """
    记忆管理工具执行器

    负责路由工具调用到对应的执行函数
    """

    def __init__(self, memory: "LoomMemory"):
        """
        初始化执行器

        Args:
            memory: LoomMemory实例
        """
        self.memory = memory

        # 工具名称到执行函数的映射
        self._executors = {
            "get_memory_stats": self._execute_get_memory_stats,
            "promote_task_to_l2": self._execute_promote_task_to_l2,
            "create_task_summary": self._execute_create_task_summary,
        }

    async def execute(self, tool_name: str, args: dict) -> dict[str, Any]:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            执行结果

        Raises:
            ValueError: 如果工具名称不存在
        """
        executor = self._executors.get(tool_name)
        if not executor:
            raise ValueError(f"Unknown memory management tool: {tool_name}")

        return await executor(args)

    async def _execute_get_memory_stats(self, args: dict) -> dict[str, Any]:
        return await execute_get_memory_stats_tool(args, self.memory)

    async def _execute_promote_task_to_l2(self, args: dict) -> dict[str, Any]:
        return await execute_promote_task_to_l2_tool(args, self.memory)

    async def _execute_create_task_summary(self, args: dict) -> dict[str, Any]:
        return await execute_create_task_summary_tool(args, self.memory)
