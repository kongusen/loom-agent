"""
05_event_bus.py - 事件总线

演示：
- EventBus 创建和使用
- 任务处理器注册
- 任务发布和路由
"""

import asyncio
from loom.events import EventBus
from loom.runtime import Task, TaskStatus


async def main():
    # 1. 创建事件总线
    event_bus = EventBus()

    # 2. 定义任务处理器
    async def handle_execute(task: Task) -> Task:
        """处理 execute 类型的任务"""
        print(f"处理任务: {task.taskId}")
        print(f"  来源: {task.sourceAgent}")
        print(f"  目标: {task.targetAgent}")
        print(f"  参数: {task.parameters}")

        # 更新任务状态和结果
        task.status = TaskStatus.COMPLETED
        task.result = {"message": "任务执行成功", "data": task.parameters}
        return task

    async def handle_query(task: Task) -> Task:
        """处理 query 类型的任务"""
        print(f"查询任务: {task.taskId}")
        task.status = TaskStatus.COMPLETED
        task.result = {"answer": "这是查询结果"}
        return task

    # 3. 注册处理器
    event_bus.register_handler("execute", handle_execute)
    event_bus.register_handler("query", handle_query)

    print(f"已注册处理器: {list(event_bus.registered_handlers.keys())}")

    # 4. 创建并发布任务
    task1 = Task(
        taskId="task-001",
        sourceAgent="agent-a",
        targetAgent="agent-b",
        action="execute",
        parameters={"data": "hello world"},
    )

    result1 = await event_bus.publish(task1)
    print(f"\n任务1结果: {result1.result}")
    print(f"任务1状态: {result1.status}")

    # 5. 发布另一个任务
    task2 = Task(
        taskId="task-002",
        sourceAgent="agent-b",
        targetAgent="agent-c",
        action="query",
        parameters={"question": "什么是 Loom Agent?"},
    )

    result2 = await event_bus.publish(task2)
    print(f"\n任务2结果: {result2.result}")


if __name__ == "__main__":
    asyncio.run(main())
