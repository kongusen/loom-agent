"""
Interceptor - 拦截器链

运行时支持：任务执行的拦截和处理。

设计原则：
1. 责任链模式 - 拦截器链式调用
2. 前后拦截 - 支持before和after拦截
3. 可组合 - 拦截器可以组合使用

内置拦截器：
- LoggingInterceptor: 日志记录
- TimingInterceptor: 性能监控
- MetricsInterceptor: 指标收集
"""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from loom.runtime.task import Task, TaskStatus

logger = logging.getLogger(__name__)

InterceptorFunc = Callable[[Task], Awaitable[Task]]


class Interceptor:
    """
    拦截器

    在任务执行前后进行拦截处理。
    """

    async def before(self, task: Task) -> Task:
        """
        任务执行前拦截

        Args:
            task: 任务

        Returns:
            处理后的任务
        """
        return task

    async def after(self, task: Task) -> Task:
        """
        任务执行后拦截

        Args:
            task: 任务

        Returns:
            处理后的任务
        """
        return task


class InterceptorChain:
    """
    拦截器链

    管理多个拦截器的链式调用。
    """

    def __init__(self):
        """初始化拦截器链"""
        self.interceptors: list[Interceptor] = []

    def add(self, interceptor: Interceptor) -> None:
        """
        添加拦截器

        Args:
            interceptor: 拦截器
        """
        self.interceptors.append(interceptor)

    async def execute(self, task: Task, executor: InterceptorFunc) -> Task:
        """
        执行拦截器链

        Args:
            task: 任务
            executor: 实际执行函数

        Returns:
            执行后的任务
        """
        # Before拦截
        for interceptor in self.interceptors:
            task = await interceptor.before(task)

        # 执行任务
        task = await executor(task)

        # After拦截（逆序）
        for interceptor in reversed(self.interceptors):
            task = await interceptor.after(task)

        return task


# ==================== 内置拦截器 ====================


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
        """获取收集的指标"""
        return self.metrics.copy()
