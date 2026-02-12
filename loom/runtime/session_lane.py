"""
Session Lane - 同 session 串行控制

提供三种隔离模式：
- strict: 严格串行（默认）
- advisory: 仅警告
- none: 不控制

符合 Loom 框架原则：提供机制，应用选择策略
"""

import asyncio
import logging
from enum import StrEnum
from typing import Any

from loom.events.actions import KnowledgeAction
from loom.runtime.task import Task
from loom.runtime.interceptor import Interceptor

logger = logging.getLogger(__name__)


class SessionIsolationMode(StrEnum):
    """Session 隔离模式"""

    STRICT = "strict"  # 严格串行（默认）
    ADVISORY = "advisory"  # 仅警告
    NONE = "none"  # 不控制


class SessionLaneInterceptor(Interceptor):
    """
    同 session 串行控制拦截器

    使用 asyncio.Lock 确保同一 session_id 的任务串行执行，
    避免上下文交叉破坏记忆一致性。
    """

    def __init__(self, mode: SessionIsolationMode = SessionIsolationMode.STRICT):
        """
        初始化 Session Lane 拦截器

        Args:
            mode: 隔离模式（strict/advisory/none）
        """
        self.mode = mode
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._lock_registry = asyncio.Lock()
        self._task_locks: dict[str, asyncio.Lock] = {}  # taskId -> lock 映射
        self._lock_usage_count: dict[tuple[str, str], int] = {}  # 锁使用计数

    async def before(self, task: Task) -> Task:
        """
        执行前检查并获取锁

        Args:
            task: 任务

        Returns:
            Task: 原任务（可能被修改）
        """
        # 无 session_id 则放行
        if not task.sessionId:
            return task

        # KnowledgeAction 是 Agent 内部子操作，不参与 session 串行控制
        if task.action in (KnowledgeAction.SEARCH, KnowledgeAction.SEARCH_RESULT):
            return task

        # 使用 task.taskId 作为节点标识（因为没有 context）
        node_id = "default"
        lock_key = (node_id, task.sessionId)

        # 获取或创建锁
        async with self._lock_registry:
            if lock_key not in self._locks:
                self._locks[lock_key] = asyncio.Lock()
                self._lock_usage_count[lock_key] = 0
            lock = self._locks[lock_key]
            self._lock_usage_count[lock_key] += 1

        # 根据模式处理
        if self.mode == SessionIsolationMode.STRICT:
            # 严格模式：阻塞等待
            await lock.acquire()
            self._task_locks[task.taskId] = lock
            # 保存 lock_key 用于 after 清理
            task.metadata["_session_lane_lock_key"] = lock_key
            logger.debug(f"Session lane acquired for session {task.sessionId}")

        elif self.mode == SessionIsolationMode.ADVISORY:
            # 警告模式：检测并发但不阻塞
            if lock.locked():
                logger.warning(
                    f"Concurrent execution detected for session {task.sessionId}. "
                    f"Consider using strict mode."
                )

        # NONE 模式：什么都不做

        return task

    async def after(self, task: Task) -> Task:
        """
        执行后释放锁

        Args:
            task: 任务

        Returns:
            Task: 原任务（可能被修改）
        """
        lock = self._task_locks.pop(task.taskId, None)
        if lock and lock.locked():
            lock.release()
            logger.debug(f"Session lane released for session {task.sessionId}")

        # 清理锁使用计数
        lock_key = task.metadata.pop("_session_lane_lock_key", None)
        if lock_key:
            async with self._lock_registry:
                if lock_key in self._lock_usage_count:
                    self._lock_usage_count[lock_key] -= 1
                    # 当没有任务使用该锁时，清理它
                    if self._lock_usage_count[lock_key] <= 0:
                        self._locks.pop(lock_key, None)
                        self._lock_usage_count.pop(lock_key, None)

        return task

    # ==================== 状态检查方法 ====================

    @property
    def active_task_ids(self) -> list[str]:
        """当前持有锁的任务ID列表"""
        return list(self._task_locks.keys())

    @property
    def active_locks_count(self) -> int:
        """当前活跃的锁数量"""
        return len(self._locks)

    def get_lock_stats(self) -> dict[str, Any]:
        """获取锁统计信息"""
        return {
            "active_locks": len(self._locks),
            "active_tasks": len(self._task_locks),
            "lock_usage": dict(self._lock_usage_count),
        }
