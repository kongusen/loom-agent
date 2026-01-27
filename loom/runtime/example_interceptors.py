"""
示例拦截器 (Example Interceptors)

提供常用的拦截器实现，用于日志、性能监控等场景。
"""

import logging
import time
from typing import Any

from loom.protocol import Task
from loom.runtime.interceptor import Interceptor

logger = logging.getLogger(__name__)


class LoggingInterceptor(Interceptor):
    """
    日志拦截器

    记录任务执行的开始和结束。
    """

    def __init__(self, log_level: int = logging.INFO):
        """
        初始化日志拦截器

        Args:
            log_level: 日志级别
        """
        self.log_level = log_level

    async def before(self, task: Task) -> Task:
        """任务执行前记录日志"""
        logger.log(
            self.log_level,
            f"[{task.task_id}] Starting task: {task.action}",
        )
        return task

    async def after(self, task: Task) -> Task:
        """任务执行后记录日志"""
        logger.log(
            self.log_level,
            f"[{task.task_id}] Completed task: {task.action} (status: {task.status})",
        )
        return task


class TimingInterceptor(Interceptor):
    """
    性能监控拦截器

    记录任务执行时间，并将时间信息添加到任务元数据中。
    """

    async def before(self, task: Task) -> Task:
        """任务执行前记录开始时间"""
        task.metadata["_timing_start"] = time.time()
        return task

    async def after(self, task: Task) -> Task:
        """任务执行后计算执行时间"""
        if "_timing_start" in task.metadata:
            start_time = task.metadata.pop("_timing_start")
            duration = time.time() - start_time
            task.metadata["execution_duration"] = duration

            logger.debug(f"[{task.task_id}] Execution time: {duration:.3f}s")

        return task


class MetricsInterceptor(Interceptor):
    """
    指标收集拦截器

    收集任务执行的统计指标。
    """

    def __init__(self):
        """初始化指标收集器"""
        self.metrics: dict[str, Any] = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_duration": 0.0,
        }

    async def before(self, task: Task) -> Task:
        """任务执行前更新指标"""
        self.metrics["total_tasks"] += 1
        task.metadata["_metrics_start"] = time.time()
        return task

    async def after(self, task: Task) -> Task:
        """任务执行后更新指标"""
        # 更新完成/失败计数
        from loom.protocol import TaskStatus

        if task.status == TaskStatus.COMPLETED:
            self.metrics["completed_tasks"] += 1
        elif task.status == TaskStatus.FAILED:
            self.metrics["failed_tasks"] += 1

        # 更新总执行时间
        if "_metrics_start" in task.metadata:
            start_time = task.metadata.pop("_metrics_start")
            duration = time.time() - start_time
            self.metrics["total_duration"] += duration

        return task

    def get_metrics(self) -> dict[str, Any]:
        """
        获取收集的指标

        Returns:
            指标字典
        """
        return self.metrics.copy()
