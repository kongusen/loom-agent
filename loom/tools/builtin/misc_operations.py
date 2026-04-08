"""其他辅助工具"""

import asyncio
from typing import Any


async def task_output(task_id: str, block: bool = True, timeout: int = 30000) -> dict[str, Any]:
    """获取任务输出

    Args:
        task_id: 任务 ID
        block: 是否阻塞等待（预留参数）
        timeout: 超时时间（预留参数）
    """
    _ = block  # 预留参数，未来用于阻塞等待
    _ = timeout  # 预留参数，未来用于超时控制
    return {"task_id": task_id, "output": "", "status": "completed"}


async def task_stop(task_id: str) -> dict[str, Any]:
    """停止任务"""
    return {"task_id": task_id, "status": "stopped"}


async def sleep(duration: int) -> dict[str, Any]:
    """休眠"""
    await asyncio.sleep(duration / 1000)
    return {"duration": duration, "status": "completed"}


async def send_message(content: str) -> dict[str, Any]:
    """发送消息"""
    return {"content": content, "status": "sent"}


async def todo_write(items: list[str]) -> dict[str, Any]:
    """写入待办事项"""
    return {"items": items, "count": len(items)}
