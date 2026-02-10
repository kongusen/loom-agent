"""
16_interceptors.py - 拦截器示例

演示：
- 自定义拦截器实现
- 日志拦截器
- 性能监控拦截器
- 指标收集拦截器
- 拦截器链组合
"""

import asyncio
import logging
import time
from typing import Any

from loom.runtime import Task, TaskStatus, Interceptor, InterceptorChain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 自定义拦截器 ====================


class LoggingInterceptor(Interceptor):
    """日志拦截器 - 记录任务执行的开始和结束"""

    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level

    async def before(self, task: Task) -> Task:
        logger.log(self.log_level, f"[{task.task_id}] Starting: {task.action}")
        return task

    async def after(self, task: Task) -> Task:
        logger.log(self.log_level, f"[{task.task_id}] Completed: {task.action} ({task.status})")
        return task


class TimingInterceptor(Interceptor):
    """性能监控拦截器 - 记录任务执行时间"""

    async def before(self, task: Task) -> Task:
        task.metadata["_timing_start"] = time.time()
        return task

    async def after(self, task: Task) -> Task:
        if "_timing_start" in task.metadata:
            start_time = task.metadata.pop("_timing_start")
            duration = time.time() - start_time
            task.metadata["execution_duration"] = duration
            logger.debug(f"[{task.task_id}] Duration: {duration:.3f}s")
        return task


class MetricsInterceptor(Interceptor):
    """指标收集拦截器 - 收集任务执行统计"""

    def __init__(self):
        self.metrics: dict[str, Any] = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_duration": 0.0,
        }

    async def before(self, task: Task) -> Task:
        self.metrics["total_tasks"] += 1
        task.metadata["_metrics_start"] = time.time()
        return task

    async def after(self, task: Task) -> Task:
        if task.status == TaskStatus.COMPLETED:
            self.metrics["completed_tasks"] += 1
        elif task.status == TaskStatus.FAILED:
            self.metrics["failed_tasks"] += 1

        if "_metrics_start" in task.metadata:
            start_time = task.metadata.pop("_metrics_start")
            self.metrics["total_duration"] += time.time() - start_time

        return task

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.copy()


# ==================== Demo ====================


async def main():
    print("=" * 60)
    print("拦截器 Demo")
    print("=" * 60)

    # 1. 创建拦截器
    print("\n[1] 创建拦截器")
    logging_interceptor = LoggingInterceptor()
    timing_interceptor = TimingInterceptor()
    metrics_interceptor = MetricsInterceptor()

    # 2. 创建拦截器链
    print("\n[2] 创建拦截器链")
    chain = InterceptorChain()
    chain.add(logging_interceptor)
    chain.add(timing_interceptor)
    chain.add(metrics_interceptor)
    print(f"    拦截器数量: {len(chain.interceptors)}")

    # 3. 模拟任务执行
    print("\n[3] 执行任务（通过拦截器链）")

    async def execute_task(task: Task) -> Task:
        """模拟任务执行"""
        await asyncio.sleep(0.1)  # 模拟耗时操作
        task.status = TaskStatus.COMPLETED
        task.result = {"message": "Task completed"}
        return task

    # 执行多个任务
    for i in range(3):
        task = Task(
            action="demo.task",
            parameters={"index": i},
        )
        result = await chain.execute(task, execute_task)
        print(f"    任务 {i+1} 结果: {result.status}")

    # 4. 查看指标
    print("\n[4] 查看收集的指标")
    metrics = metrics_interceptor.get_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.3f}")
        else:
            print(f"    {key}: {value}")

    print("\n" + "=" * 60)
    print("Demo 完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
