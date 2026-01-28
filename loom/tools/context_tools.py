"""
Context Query Tools - LLM主动查询上下文

基于"框架提供能力，LLM做决策"的原则，将上下文管理从框架硬编码转换为LLM主动查询。

核心工具：
1. Memory查询工具 - 让LLM主动选择查询哪个记忆层
2. Event查询工具 - 让LLM主动选择查询哪种事件类型
3. Context总结工具 - 让LLM决定如何处理token限制

使用方式：
    from loom.tools.context_tools import create_context_tools

    agent = Agent(
        tools=[...] + create_context_tools(memory, event_bus),
    )
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.events.event_bus import EventBus
    from loom.memory.core import LoomMemory


# ==================== Memory Query Tools ====================


def create_query_l1_memory_tool() -> dict:
    """
    创建L1记忆查询工具定义

    L1: 最近的完整Task对象（循环缓冲区）

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_l1_memory",
            "description": "Query L1 memory (recent tasks). L1 contains the most recent complete Task objects in a circular buffer. Use this to get recent task history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tasks to retrieve (default: 10)",
                        "default": 10,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID filter",
                    },
                },
                "required": [],
            },
        },
    }


async def execute_query_l1_memory_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行L1记忆查询

    Args:
        args: 工具参数 {"limit": 10}
        memory: LoomMemory实例

    Returns:
        查询结果
    """
    limit = args.get("limit", 10)
    session_id = args.get("session_id")
    tasks = memory.get_l1_tasks(limit=limit, session_id=session_id)

    return {
        "layer": "L1",
        "description": "Recent tasks (circular buffer)",
        "count": len(tasks),
        "tasks": [
            {
                "task_id": task.task_id,
                "action": task.action,
                "parameters": task.parameters,
                "result": task.result,
                "status": task.status.value if task.status else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            for task in tasks
        ],
    }


def create_query_l2_memory_tool() -> dict:
    """
    创建L2记忆查询工具定义

    L2: 会话工作记忆（按重要性排序，以压缩陈述句形式返回）

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_l2_memory",
            "description": "Query L2 memory (session working memory). L2 contains important tasks in compressed statement form. Use this to get high-priority task history without full details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tasks to retrieve (default: 10)",
                        "default": 10,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID filter",
                    },
                },
                "required": [],
            },
        },
    }


async def execute_query_l2_memory_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行L2记忆查询（返回压缩陈述句）

    Args:
        args: 工具参数 {"limit": 10}
        memory: LoomMemory实例

    Returns:
        查询结果（压缩陈述句格式）
    """
    limit = args.get("limit", 10)
    session_id = args.get("session_id")
    tasks = memory.get_l2_tasks(limit=limit, session_id=session_id)

    # 转换为压缩陈述句（L2级别压缩）
    statements = []
    for task in tasks:
        # 格式: "执行了[action]，参数[params]，结果[result]"
        params_str = (
            str(task.parameters)[:50] + "..."
            if len(str(task.parameters)) > 50
            else str(task.parameters)
        )
        result_str = (
            str(task.result)[:100] + "..."
            if task.result and len(str(task.result)) > 100
            else str(task.result or "无结果")
        )

        statement = f"执行了{task.action}操作，参数{params_str}，结果{result_str}"
        statements.append(
            {
                "task_id": task.task_id,
                "statement": statement,
                "importance": task.metadata.get("importance", 0.5),
            }
        )

    return {
        "layer": "L2",
        "description": "Important tasks (compressed statements)",
        "count": len(statements),
        "statements": statements,
    }


def create_query_l3_memory_tool() -> dict:
    """
    创建L3记忆查询工具定义

    L3: 会话摘要（高度压缩的陈述句）

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_l3_memory",
            "description": "Query L3 memory (session summaries). L3 contains highly compressed task summaries in statement form. Use this to get a broad overview of session history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of summaries to retrieve (default: 20)",
                        "default": 20,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID filter",
                    },
                },
                "required": [],
            },
        },
    }


async def execute_query_l3_memory_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行L3记忆查询（返回高度压缩陈述句）

    Args:
        args: 工具参数 {"limit": 20}
        memory: LoomMemory实例

    Returns:
        查询结果（高度压缩陈述句格式）
    """
    limit = args.get("limit", 20)
    session_id = args.get("session_id")
    summaries = memory.get_l3_summaries(limit=limit, session_id=session_id)

    # 转换为高度压缩陈述句（L3级别压缩）
    statements = []
    for summary in summaries:
        # 格式: "[action]: [简短描述]"
        result_brief = (
            summary.result_summary[:50] + "..."
            if len(summary.result_summary) > 50
            else summary.result_summary
        )
        statement = f"{summary.action}: {result_brief}"

        statements.append(
            {
                "task_id": summary.task_id,
                "statement": statement,
                "tags": summary.tags[:3] if summary.tags else [],  # 只保留前3个标签
            }
        )

    return {
        "layer": "L3",
        "description": "Task summaries (highly compressed statements)",
        "count": len(statements),
        "statements": statements,
    }


def create_query_l4_memory_tool() -> dict:
    """
    创建L4记忆查询工具定义

    L4: 向量存储（语义检索）

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_l4_memory",
            "description": "Query L4 memory (semantic search). L4 uses vector storage for semantic retrieval. Use this to find tasks related to a specific query or concept.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for semantic matching",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to retrieve (default: 5)",
                        "default": 5,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID filter (applies to fallback search)",
                    },
                },
                "required": ["query"],
            },
        },
    }


async def execute_query_l4_memory_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行L4记忆查询（语义搜索，返回极简陈述句）

    Args:
        args: 工具参数 {"query": "...", "limit": 5}
        memory: LoomMemory实例

    Returns:
        查询结果（极简陈述句格式）
    """
    query = args.get("query", "")
    limit = args.get("limit", 5)
    session_id = args.get("session_id")

    tasks = await memory.search_tasks(query=query, limit=limit, session_id=session_id)

    # 转换为极简陈述句（L4级别压缩 - 最高压缩）
    statements = []
    for task in tasks:
        # 格式: "[action]完成" 或 "[action]失败"
        status = "完成" if task.status and task.status.value == "completed" else "执行"
        statement = f"{task.action}{status}"

        statements.append(
            {
                "task_id": task.task_id,
                "statement": statement,
            }
        )

    return {
        "layer": "L4",
        "description": "Semantic search results (minimal statements)",
        "query": query,
        "count": len(statements),
        "statements": statements,
    }


# ==================== Event Query Tools ====================


def create_query_events_by_action_tool() -> dict:
    """
    创建按动作类型查询事件工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_events_by_action",
            "description": "Query events by action type. Use this to find specific types of events (e.g., 'node.thinking', 'node.tool_call', 'node.observation').",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action type to filter by (e.g., 'node.thinking', 'node.tool_call')",
                    },
                    "node_filter": {
                        "type": "string",
                        "description": "Optional node ID to filter by",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of events to retrieve (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["action"],
            },
        },
    }


async def execute_query_events_by_action_tool(args: dict, event_bus: "EventBus") -> dict[str, Any]:
    """
    执行按动作类型查询事件

    Args:
        args: 工具参数 {"action": "...", "node_filter": "...", "limit": 10}
        event_bus: EventBus实例

    Returns:
        查询结果
    """
    action = args.get("action", "")
    node_filter = args.get("node_filter")
    limit = args.get("limit", 10)

    events = event_bus.query_by_action(action=action, node_filter=node_filter, limit=limit)

    return {
        "query_type": "by_action",
        "action": action,
        "node_filter": node_filter,
        "count": len(events),
        "events": [
            {
                "task_id": event.task_id,
                "action": event.action,
                "parameters": event.parameters,
                "result": event.result,
                "status": event.status.value if event.status else None,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
    }


def create_query_events_by_node_tool() -> dict:
    """
    创建按节点查询事件工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_events_by_node",
            "description": "Query events by node ID. Use this to find all events from a specific agent/node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "Node ID to filter by",
                    },
                    "action_filter": {
                        "type": "string",
                        "description": "Optional action type to filter by",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of events to retrieve (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["node_id"],
            },
        },
    }


async def execute_query_events_by_node_tool(args: dict, event_bus: "EventBus") -> dict[str, Any]:
    """
    执行按节点查询事件

    Args:
        args: 工具参数 {"node_id": "...", "action_filter": "...", "limit": 10}
        event_bus: EventBus实例

    Returns:
        查询结果
    """
    node_id = args.get("node_id", "")
    action_filter = args.get("action_filter")
    limit = args.get("limit", 10)

    events = event_bus.query_by_node(node_id=node_id, action_filter=action_filter, limit=limit)

    return {
        "query_type": "by_node",
        "node_id": node_id,
        "action_filter": action_filter,
        "count": len(events),
        "events": [
            {
                "task_id": event.task_id,
                "action": event.action,
                "parameters": event.parameters,
                "result": event.result,
                "status": event.status.value if event.status else None,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
    }


def create_query_events_by_target_tool() -> dict:
    """
    创建按目标查询事件工具（点对点）

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_events_by_target",
            "description": "Query events by target agent or target node (direct messages). Use this to retrieve point-to-point messages sent to a specific agent or node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_agent": {
                        "type": "string",
                        "description": "Target agent ID",
                    },
                    "target_node_id": {
                        "type": "string",
                        "description": "Target node ID (optional)",
                    },
                    "action_filter": {
                        "type": "string",
                        "description": "Optional action filter",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of events to retrieve (default: 10)",
                        "default": 10,
                    },
                },
                "required": [],
            },
        },
    }


async def execute_query_events_by_target_tool(args: dict, event_bus: "EventBus") -> dict[str, Any]:
    """
    执行按目标查询事件

    Args:
        args: 工具参数
        event_bus: EventBus实例

    Returns:
        查询结果
    """
    target_agent = args.get("target_agent")
    target_node_id = args.get("target_node_id")
    action_filter = args.get("action_filter")
    limit = args.get("limit", 10)

    if not target_agent and not target_node_id:
        return {
            "query_type": "by_target",
            "error": "target_agent or target_node_id is required",
            "count": 0,
            "events": [],
        }

    events = event_bus.query_by_target(
        target_agent=target_agent,
        target_node_id=target_node_id,
        action_filter=action_filter,
        limit=limit,
    )

    return {
        "query_type": "by_target",
        "target_agent": target_agent,
        "target_node_id": target_node_id,
        "count": len(events),
        "events": [
            {
                "task_id": event.task_id,
                "action": event.action,
                "parameters": event.parameters,
                "status": event.status.value if event.status else None,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
    }


def create_query_recent_events_tool() -> dict:
    """
    创建查询最近事件工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_recent_events",
            "description": "Query recent events across all nodes. Use this to get a general overview of recent activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of events to retrieve (default: 10)",
                        "default": 10,
                    },
                    "action_filter": {
                        "type": "string",
                        "description": "Optional action type to filter by",
                    },
                    "node_filter": {
                        "type": "string",
                        "description": "Optional node ID to filter by",
                    },
                },
                "required": [],
            },
        },
    }


async def execute_query_recent_events_tool(args: dict, event_bus: "EventBus") -> dict[str, Any]:
    """
    执行查询最近事件

    Args:
        args: 工具参数 {"limit": 10, "action_filter": "...", "node_filter": "..."}
        event_bus: EventBus实例

    Returns:
        查询结果
    """
    limit = args.get("limit", 10)
    action_filter = args.get("action_filter")
    node_filter = args.get("node_filter")

    events = event_bus.query_recent(
        limit=limit, action_filter=action_filter, node_filter=node_filter
    )

    return {
        "query_type": "recent",
        "action_filter": action_filter,
        "node_filter": node_filter,
        "count": len(events),
        "events": [
            {
                "task_id": event.task_id,
                "action": event.action,
                "parameters": event.parameters,
                "result": event.result,
                "status": event.status.value if event.status else None,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
    }


def create_query_thinking_process_tool() -> dict:
    """
    创建查询思考过程工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_thinking_process",
            "description": "Query thinking process events. Use this to see what other agents or yourself have been thinking about.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "Optional node ID to filter by",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Optional task ID to filter by",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of thoughts to retrieve (default: 10)",
                        "default": 10,
                    },
                },
                "required": [],
            },
        },
    }


async def execute_query_thinking_process_tool(args: dict, event_bus: "EventBus") -> dict[str, Any]:
    """
    执行查询思考过程

    Args:
        args: 工具参数 {"node_id": "...", "task_id": "...", "limit": 10}
        event_bus: EventBus实例

    Returns:
        查询结果
    """
    node_id = args.get("node_id")
    task_id = args.get("task_id")
    limit = args.get("limit", 10)

    thoughts = event_bus.query_thinking_process(node_id=node_id, task_id=task_id, limit=limit)

    return {
        "query_type": "thinking_process",
        "node_id": node_id,
        "task_id": task_id,
        "count": len(thoughts),
        "thoughts": thoughts,
    }


# ==================== Helper Functions ====================


def create_all_context_tools() -> list[dict]:
    """
    创建所有上下文查询工具

    Returns:
        所有工具定义的列表
    """
    return [
        # Memory tools
        create_query_l1_memory_tool(),
        create_query_l2_memory_tool(),
        create_query_l3_memory_tool(),
        create_query_l4_memory_tool(),
        # Event tools
        create_query_events_by_action_tool(),
        create_query_events_by_node_tool(),
        create_query_events_by_target_tool(),
        create_query_recent_events_tool(),
        create_query_thinking_process_tool(),
    ]


class ContextToolExecutor:
    """
    上下文工具执行器

    负责路由工具调用到对应的执行函数
    """

    def __init__(self, memory: "LoomMemory", event_bus: "EventBus"):
        """
        初始化执行器

        Args:
            memory: LoomMemory实例
            event_bus: EventBus实例
        """
        self.memory = memory
        self.event_bus = event_bus

        # 工具名称到执行函数的映射
        self._executors = {
            "query_l1_memory": self._execute_query_l1_memory,
            "query_l2_memory": self._execute_query_l2_memory,
            "query_l3_memory": self._execute_query_l3_memory,
            "query_l4_memory": self._execute_query_l4_memory,
            "query_events_by_action": self._execute_query_events_by_action,
            "query_events_by_node": self._execute_query_events_by_node,
            "query_events_by_target": self._execute_query_events_by_target,
            "query_recent_events": self._execute_query_recent_events,
            "query_thinking_process": self._execute_query_thinking_process,
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
            raise ValueError(f"Unknown context tool: {tool_name}")

        return await executor(args)

    # Memory tool executors
    async def _execute_query_l1_memory(self, args: dict) -> dict[str, Any]:
        return await execute_query_l1_memory_tool(args, self.memory)

    async def _execute_query_l2_memory(self, args: dict) -> dict[str, Any]:
        return await execute_query_l2_memory_tool(args, self.memory)

    async def _execute_query_l3_memory(self, args: dict) -> dict[str, Any]:
        return await execute_query_l3_memory_tool(args, self.memory)

    async def _execute_query_l4_memory(self, args: dict) -> dict[str, Any]:
        return await execute_query_l4_memory_tool(args, self.memory)

    # Event tool executors
    async def _execute_query_events_by_action(self, args: dict) -> dict[str, Any]:
        return await execute_query_events_by_action_tool(args, self.event_bus)

    async def _execute_query_events_by_node(self, args: dict) -> dict[str, Any]:
        return await execute_query_events_by_node_tool(args, self.event_bus)

    async def _execute_query_events_by_target(self, args: dict) -> dict[str, Any]:
        return await execute_query_events_by_target_tool(args, self.event_bus)

    async def _execute_query_recent_events(self, args: dict) -> dict[str, Any]:
        return await execute_query_recent_events_tool(args, self.event_bus)

    async def _execute_query_thinking_process(self, args: dict) -> dict[str, Any]:
        return await execute_query_thinking_process_tool(args, self.event_bus)
