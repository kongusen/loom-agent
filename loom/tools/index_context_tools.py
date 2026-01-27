"""
Index-Based Context Tools - 基于索引的上下文操作

优化LLM的token使用，通过两阶段查询：
1. 列出索引+简短预览（减少token）
2. 根据索引选择完整内容（精确控制）

核心优势：
- 减少LLM输出token（只输出索引）
- 提高查询效率
- 更精确的上下文控制

使用方式：
    # 阶段1：列出可用记忆
    result = list_l2_memory(limit=10)
    # 返回：[1] file_read操作 [2] file_write操作 ...

    # 阶段2：选择需要的索引
    content = select_memory_by_index(indices=[1, 3, 5])
    # 返回完整陈述句
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory

from loom.protocol import Task

# ==================== List Tools (阶段1：列出索引) ====================


def create_list_l2_memory_tool() -> dict:
    """
    创建列出L2记忆索引工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "list_l2_memory",
            "description": "List L2 memory items with index and preview. Returns indexed list of important tasks for efficient browsing. Use this first to see what's available, then use select_memory_by_index to get full content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of items to list (default: 10)",
                        "default": 10,
                    }
                },
                "required": [],
            },
        },
    }


async def execute_list_l2_memory_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行列出L2记忆索引

    Args:
        args: 工具参数 {"limit": 10}
        memory: LoomMemory实例

    Returns:
        索引列表（简短预览）
    """
    limit = args.get("limit", 10)
    tasks = memory.get_l2_tasks(limit=limit)

    # 生成索引+预览列表
    items = []
    for idx, task in enumerate(tasks, start=1):
        # 简短预览：只显示action和简短描述
        preview = f"{task.action}"
        if task.parameters:
            # 只显示第一个参数的key
            first_param = list(task.parameters.keys())[0] if task.parameters else ""
            if first_param:
                preview += f"({first_param}=...)"

        items.append(
            {
                "index": idx,
                "task_id": task.task_id,
                "preview": preview,
                "importance": task.metadata.get("importance", 0.5),
            }
        )

    return {
        "layer": "L2",
        "description": "Important tasks (indexed preview)",
        "count": len(items),
        "items": items,
        "hint": "Use select_memory_by_index([1,3,5]) to get full content",
    }


def create_list_l3_memory_tool() -> dict:
    """
    创建列出L3记忆索引工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "list_l3_memory",
            "description": "List L3 memory items with index and preview. Returns indexed list of compressed task summaries for efficient browsing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of items to list (default: 20)",
                        "default": 20,
                    }
                },
                "required": [],
            },
        },
    }


async def execute_list_l3_memory_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行列出L3记忆索引

    Args:
        args: 工具参数 {"limit": 20}
        memory: LoomMemory实例

    Returns:
        索引列表（简短预览）
    """
    limit = args.get("limit", 20)
    summaries = memory.get_l3_summaries(limit=limit)

    # 生成索引+预览列表
    items = []
    for idx, summary in enumerate(summaries, start=1):
        # 极简预览：只显示action
        preview = f"{summary.action}"

        items.append(
            {
                "index": idx,
                "task_id": summary.task_id,
                "preview": preview,
                "tags": summary.tags[:2] if summary.tags else [],  # 只显示前2个标签
            }
        )

    return {
        "layer": "L3",
        "description": "Task summaries (indexed preview)",
        "count": len(items),
        "items": items,
        "hint": "Use select_memory_by_index([1,3,5]) to get full content",
    }


# ==================== Select Tools (阶段2：选择索引) ====================


def create_select_memory_by_index_tool() -> dict:
    """
    创建根据索引选择记忆工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "select_memory_by_index",
            "description": "Select memory items by their indices to get full content. Use this after list_l2_memory or list_l3_memory to retrieve complete statements for selected items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "layer": {
                        "type": "string",
                        "enum": ["L2", "L3"],
                        "description": "Memory layer to select from (L2 or L3)",
                    },
                    "indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of indices to select (e.g., [1, 3, 5])",
                    },
                },
                "required": ["layer", "indices"],
            },
        },
    }


async def execute_select_memory_by_index_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行根据索引选择记忆

    Args:
        args: 工具参数 {"layer": "L2", "indices": [1, 3, 5]}
        memory: LoomMemory实例

    Returns:
        选中项的完整内容
    """
    layer = args.get("layer", "L2")
    indices = args.get("indices", [])

    if not indices:
        return {
            "error": "No indices provided",
            "selected": [],
        }

    # 根据层级获取数据
    from loom.memory.types import TaskSummary

    if layer == "L2":
        items: list[Task] = memory.get_l2_tasks(limit=100)  # 获取足够多的项
    elif layer == "L3":
        l3_items: list[TaskSummary] = memory.get_l3_summaries(limit=100)
        # 将 TaskSummary 转换为类似 Task 的结构以便统一处理
        items = l3_items  # type: ignore[assignment]
    else:
        return {
            "error": f"Invalid layer: {layer}",
            "selected": [],
        }

    # 根据索引选择项（索引从1开始）
    selected: list[dict[str, Any]] = []
    for idx in indices:
        if 1 <= idx <= len(items):
            item = items[idx - 1]  # 转换为0-based索引

            if layer == "L2":
                # L2: 返回中等压缩陈述句
                if isinstance(item, Task):
                    params_str = (
                        str(item.parameters)[:50] + "..."
                        if len(str(item.parameters)) > 50
                        else str(item.parameters)
                    )
                    result_str = (
                        str(item.result)[:100] + "..."
                        if item.result and len(str(item.result)) > 100
                        else str(item.result or "无结果")
                    )
                    statement = f"执行了{item.action}操作，参数{params_str}，结果{result_str}"

                    selected.append(
                        {
                            "index": idx,
                            "task_id": item.task_id,
                            "statement": statement,
                        }
                    )
            elif layer == "L3" and isinstance(item, TaskSummary):
                # L3: 返回高度压缩陈述句
                result_brief = (
                    item.result_summary[:50] + "..."
                    if len(item.result_summary) > 50
                    else item.result_summary
                )
                statement = f"{item.action}: {result_brief}"

                selected.append(
                    {
                        "index": idx,
                        "task_id": item.task_id,
                        "statement": statement,
                    }
                )

    return {
        "layer": layer,
        "description": f"Selected {len(selected)} items from {layer}",
        "count": len(selected),
        "selected": selected,
    }


# ==================== Helper Functions ====================


def create_all_index_context_tools() -> list[dict]:
    """
    创建所有基于索引的上下文工具

    Returns:
        所有工具定义的列表
    """
    return [
        create_list_l2_memory_tool(),
        create_list_l3_memory_tool(),
        create_select_memory_by_index_tool(),
    ]


class IndexContextToolExecutor:
    """
    基于索引的上下文工具执行器

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
            "list_l2_memory": self._execute_list_l2_memory,
            "list_l3_memory": self._execute_list_l3_memory,
            "select_memory_by_index": self._execute_select_memory_by_index,
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
            raise ValueError(f"Unknown index context tool: {tool_name}")

        return await executor(args)

    async def _execute_list_l2_memory(self, args: dict) -> dict[str, Any]:
        return await execute_list_l2_memory_tool(args, self.memory)

    async def _execute_list_l3_memory(self, args: dict) -> dict[str, Any]:
        return await execute_list_l3_memory_tool(args, self.memory)

    async def _execute_select_memory_by_index(self, args: dict) -> dict[str, Any]:
        return await execute_select_memory_by_index_tool(args, self.memory)
