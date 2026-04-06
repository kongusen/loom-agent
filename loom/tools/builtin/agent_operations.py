"""Agent 协作工具"""

from typing import Any


async def spawn_agent(task: str, depth: int = 1) -> dict[str, Any]:
    """生成子 Agent"""
    return {
        "agent_id": f"agent_{depth}",
        "task": task,
        "depth": depth,
        "status": "spawned"
    }


async def ask_user(question: str, options: list[str]) -> dict[str, Any]:
    """询问用户"""
    return {
        "question": question,
        "options": options,
        "answer": None  # 需要用户输入
    }
