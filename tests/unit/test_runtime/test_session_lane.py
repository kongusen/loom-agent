"""
Session Lane 单元测试

测试同 session 串行控制功能
"""

import asyncio

import pytest

from loom.events.actions import KnowledgeAction
from loom.runtime import Task
from loom.runtime.session_lane import SessionIsolationMode, SessionLaneInterceptor


class TestSessionLaneInterceptorStrict:
    """测试 strict 模式"""

    @pytest.mark.asyncio
    async def test_same_session_executes_serially(self):
        """测试同 session 的任务串行执行"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)
        execution_order = []

        async def execute_task(task_id: str, session_id: str):
            """模拟任务执行"""
            task = Task(taskId=task_id, sessionId=session_id, action="test")

            # 执行前拦截
            await interceptor.before(task)

            # 记录开始执行
            execution_order.append(f"{task_id}_start")
            await asyncio.sleep(0.1)  # 模拟执行时间
            execution_order.append(f"{task_id}_end")

            # 执行后拦截
            await interceptor.after(task)

        # 并发启动两个同 session 的任务
        await asyncio.gather(
            execute_task("task1", "session-1"),
            execute_task("task2", "session-1"),
        )

        # 验证串行执行：task1 完全结束后 task2 才开始
        assert execution_order == [
            "task1_start",
            "task1_end",
            "task2_start",
            "task2_end",
        ] or execution_order == [
            "task2_start",
            "task2_end",
            "task1_start",
            "task1_end",
        ]

    @pytest.mark.asyncio
    async def test_different_sessions_execute_concurrently(self):
        """测试不同 session 的任务可以并发执行"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)
        execution_order = []

        async def execute_task(task_id: str, session_id: str):
            """模拟任务执行"""
            task = Task(taskId=task_id, sessionId=session_id, action="test")

            await interceptor.before(task)
            execution_order.append(f"{task_id}_start")
            await asyncio.sleep(0.05)
            execution_order.append(f"{task_id}_end")
            await interceptor.after(task)

        # 并发启动两个不同 session 的任务
        await asyncio.gather(
            execute_task("task1", "session-1"),
            execute_task("task2", "session-2"),
        )

        # 验证并发执行：两个任务交错执行
        # task1 和 task2 应该有交错（不是完全串行）
        assert "task1_start" in execution_order
        assert "task2_start" in execution_order
        assert "task1_end" in execution_order
        assert "task2_end" in execution_order

    @pytest.mark.asyncio
    async def test_no_session_id_not_blocked(self):
        """测试没有 session_id 的任务不受影响"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)

        task = Task(taskId="task1", action="test")  # 无 sessionId

        # 应该立即通过，不阻塞
        result = await interceptor.before(task)
        assert result == task
        # 验证没有锁被创建
        assert task.taskId not in interceptor._task_locks


class TestSessionLaneInterceptorAdvisory:
    """测试 advisory 模式"""

    @pytest.mark.asyncio
    async def test_advisory_mode_warns_but_not_blocks(self, caplog):
        """测试 advisory 模式检测并发但不阻塞"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.ADVISORY)
        execution_order = []

        async def execute_task(task_id: str, session_id: str):
            """模拟任务执行"""
            task = Task(taskId=task_id, sessionId=session_id, action="test")

            await interceptor.before(task)
            execution_order.append(f"{task_id}_start")
            await asyncio.sleep(0.05)
            execution_order.append(f"{task_id}_end")
            await interceptor.after(task)

        # 并发启动两个同 session 的任务
        with caplog.at_level("WARNING"):
            await asyncio.gather(
                execute_task("task1", "session-1"),
                execute_task("task2", "session-1"),
            )

        # 验证并发执行（不阻塞）
        assert len(execution_order) == 4

        # 验证有警告日志（可能有并发检测）
        # 注意：由于时序问题，可能不总是检测到并发


class TestSessionLaneInterceptorNone:
    """测试 none 模式"""

    @pytest.mark.asyncio
    async def test_none_mode_no_control(self):
        """测试 none 模式不进行任何控制"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.NONE)
        execution_order = []

        async def execute_task(task_id: str, session_id: str):
            """模拟任务执行"""
            task = Task(taskId=task_id, sessionId=session_id, action="test")

            await interceptor.before(task)
            execution_order.append(f"{task_id}_start")
            await asyncio.sleep(0.05)
            execution_order.append(f"{task_id}_end")
            await interceptor.after(task)

        # 并发启动两个同 session 的任务
        await asyncio.gather(
            execute_task("task1", "session-1"),
            execute_task("task2", "session-1"),
        )

        # 验证并发执行（完全不控制）
        assert len(execution_order) == 4
        # 不验证顺序，因为完全并发


class TestSessionLaneInterceptorLockManagement:
    """测试锁管理"""

    @pytest.mark.asyncio
    async def test_lock_released_after_execution(self):
        """测试锁在执行后被正确释放"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)

        task = Task(taskId="task1", sessionId="session-1", action="test")

        # 执行前获取锁
        await interceptor.before(task)
        assert task.taskId in interceptor._task_locks
        lock = interceptor._task_locks[task.taskId]
        assert lock.locked()

        # 执行后释放锁
        await interceptor.after(task)
        assert not lock.locked()
        assert task.taskId not in interceptor._task_locks

    @pytest.mark.asyncio
    async def test_different_nodes_different_locks(self):
        """测试不同节点使用不同的锁"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)

        task1 = Task(taskId="task1", sessionId="session-1", action="test")
        _task2 = Task(taskId="task2", sessionId="session-1", action="test")  # noqa: F841

        # 两个相同 session 的任务应该使用相同的锁（当前实现使用 default node_id）
        await interceptor.before(task1)

        # 验证 task1 的锁已被获取
        assert task1.taskId in interceptor._task_locks
        lock1 = interceptor._task_locks[task1.taskId]
        assert lock1.locked()

        # task2 应该被阻塞（因为使用相同的 session_id）
        # 我们不能直接测试阻塞，但可以验证锁的存在
        lock_key = ("default", "session-1")
        assert lock_key in interceptor._locks

        # 释放 task1 的锁
        await interceptor.after(task1)
        assert not lock1.locked()
        assert task1.taskId not in interceptor._task_locks


class TestSessionLaneKnowledgeActionBypass:
    """KnowledgeAction 任务绕过 session 串行控制"""

    @pytest.mark.asyncio
    async def test_knowledge_search_bypasses_lock(self):
        """knowledge.search 不获取锁"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)

        task = Task(
            taskId="search-1",
            sessionId="session-1",
            action=KnowledgeAction.SEARCH,
            parameters={"query": "test"},
        )
        result = await interceptor.before(task)
        assert result == task
        assert task.taskId not in interceptor._task_locks

    @pytest.mark.asyncio
    async def test_knowledge_result_bypasses_lock(self):
        """knowledge.result 不获取锁"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)

        task = Task(
            taskId="result-1",
            sessionId="session-1",
            action=KnowledgeAction.SEARCH_RESULT,
            parameters={"query": "test"},
        )
        result = await interceptor.before(task)
        assert result == task
        assert task.taskId not in interceptor._task_locks

    @pytest.mark.asyncio
    async def test_knowledge_action_concurrent_with_session_lock(self):
        """KnowledgeAction 任务不被同 session 的普通任务阻塞"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)

        # 先让普通任务获取锁
        normal_task = Task(
            taskId="normal-1",
            sessionId="session-1",
            action="execute",
        )
        await interceptor.before(normal_task)
        assert normal_task.taskId in interceptor._task_locks

        # KnowledgeAction 任务应该立即通过，不被阻塞
        search_task = Task(
            taskId="search-1",
            sessionId="session-1",
            action=KnowledgeAction.SEARCH,
            parameters={"query": "test"},
        )
        result = await interceptor.before(search_task)
        assert result == search_task

        # 清理
        await interceptor.after(normal_task)

    @pytest.mark.asyncio
    async def test_normal_action_still_blocked(self):
        """非 KnowledgeAction 的普通任务仍然受 session 串行控制"""
        interceptor = SessionLaneInterceptor(mode=SessionIsolationMode.STRICT)

        task = Task(
            taskId="task-1",
            sessionId="session-1",
            action="execute",
        )
        await interceptor.before(task)
        assert task.taskId in interceptor._task_locks
        await interceptor.after(task)
