"""
Done Tool Pattern - 显式完成机制

防止 Agent 误判任务结束，要求 LLM 显式调用 done 工具来表示任务完成。

核心组件：
1. TaskComplete 异常 - 用于信号任务完成（定义在 loom.exceptions）
2. create_done_tool() - 创建 done 工具定义
3. execute_done_tool() - 执行 done 工具（抛出 TaskComplete）

使用方式：
    from loom.tools.done_tool import create_done_tool

    agent = Agent(
        tools=[..., create_done_tool()],
        require_done_tool=True,
    )
"""

from typing import NoReturn

from loom.exceptions import TaskComplete


def create_done_tool() -> dict:
    """
    创建 done 工具定义

    Returns:
        OpenAI 格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "done",
            "description": (
                "Signal task completion. Call this tool when the task is done. "
                "Your text output before this call IS the response — "
                "do NOT repeat it in the message parameter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Optional brief summary for logging. Not used as the response.",
                    },
                    "output": {
                        "type": "object",
                        "description": "Optional structured data to pass to downstream nodes in a workflow.",
                    },
                },
                "required": [],
            },
        },
    }


async def execute_done_tool(args: dict) -> NoReturn:
    """
    执行 done 工具

    Args:
        args: 工具参数 {"message": "...", "output": {...}}

    Raises:
        TaskComplete: 总是抛出此异常来信号任务完成
    """
    message = args.get("message", "Task completed")
    output = args.get("output")
    raise TaskComplete(message, output=output)
