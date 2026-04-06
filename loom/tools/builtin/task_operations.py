"""任务管理工具"""

from typing import Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Task:
    id: str
    subject: str
    description: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


_tasks: dict[str, Task] = {}
_task_counter = 0


async def task_create(subject: str, description: str) -> dict[str, Any]:
    """创建任务"""
    global _task_counter
    _task_counter += 1
    task_id = f"task_{_task_counter}"

    task = Task(id=task_id, subject=subject, description=description)
    _tasks[task_id] = task

    return {"task_id": task_id, "status": "created"}


async def task_update(task_id: str, status: str) -> dict[str, Any]:
    """更新任务状态"""
    if task_id not in _tasks:
        raise ValueError(f"Task not found: {task_id}")

    _tasks[task_id].status = status
    return {"task_id": task_id, "status": status}


async def task_list() -> dict[str, Any]:
    """列出所有任务"""
    tasks = [
        {"id": t.id, "subject": t.subject, "status": t.status}
        for t in _tasks.values()
    ]
    return {"tasks": tasks, "count": len(tasks)}


async def task_get(task_id: str) -> dict[str, Any]:
    """获取任务详情"""
    if task_id not in _tasks:
        raise ValueError(f"Task not found: {task_id}")

    task = _tasks[task_id]
    return {
        "id": task.id,
        "subject": task.subject,
        "description": task.description,
        "status": task.status
    }
