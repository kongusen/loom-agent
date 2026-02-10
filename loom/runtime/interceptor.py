"""
Interceptor - 拦截器链

运行时支持：任务执行的拦截和处理。

设计原则：
1. 责任链模式 - 拦截器链式调用
2. 前后拦截 - 支持before和after拦截
3. 可组合 - 拦截器可以组合使用
"""

from collections.abc import Awaitable, Callable

from loom.runtime import Task

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
