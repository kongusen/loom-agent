"""
Session Unit Tests

测试会话实体的核心功能
"""

import pytest

from loom.events import Session, SessionStatus
from loom.runtime import Task


class TestSessionInit:
    """测试 Session 初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        session = Session(session_id="test-session")

        assert session.session_id == "test-session"
        assert session.status == SessionStatus.ACTIVE
        assert session.is_active is True
        assert session.context_token_budget == 128000

    def test_init_custom_budgets(self):
        """测试自定义 Token 预算"""
        session = Session(
            session_id="test-session",
            l1_token_budget=4000,
            l2_token_budget=8000,
            l3_token_budget=16000,
            context_token_budget=64000,
        )

        assert session.memory.l1_token_budget == 4000
        assert session.memory.l2_token_budget == 8000
        assert session.memory.l3_token_budget == 16000
        assert session.context_token_budget == 64000


class TestSessionLifecycle:
    """测试 Session 生命周期"""

    def test_pause_and_resume(self):
        """测试暂停和恢复"""
        session = Session(session_id="test-session")

        # 暂停
        session.pause()
        assert session.status == SessionStatus.PAUSED
        assert session.is_active is False

        # 恢复
        session.resume()
        assert session.status == SessionStatus.ACTIVE
        assert session.is_active is True

    def test_end_session(self):
        """测试结束会话"""
        session = Session(session_id="test-session")

        session.end()
        assert session.status == SessionStatus.ENDED
        assert session.is_active is False

    def test_end_is_idempotent(self):
        """测试结束操作是幂等的"""
        session = Session(session_id="test-session")

        session.end()
        session.end()  # 不应抛出异常
        assert session.status == SessionStatus.ENDED

    def test_cannot_pause_ended_session(self):
        """测试不能暂停已结束的会话"""
        session = Session(session_id="test-session")
        session.end()

        with pytest.raises(RuntimeError):
            session.pause()

    def test_cannot_resume_active_session(self):
        """测试不能恢复活跃的会话"""
        session = Session(session_id="test-session")

        with pytest.raises(RuntimeError):
            session.resume()


class TestSessionMemory:
    """测试 Session Memory 代理方法"""

    def test_add_task(self):
        """测试添加任务"""
        session = Session(session_id="test-session")
        task = Task(task_id="task-1", action="test_action")

        session.add_task(task)

        # 任务应该被添加到 Memory
        tasks = session.get_l1_tasks(limit=10)
        assert len(tasks) == 1
        assert tasks[0].task_id == "task-1"
        # session_id 应该被自动注入
        assert tasks[0].session_id == "test-session"

    def test_cannot_add_task_to_ended_session(self):
        """测试不能向已结束的会话添加任务"""
        session = Session(session_id="test-session")
        session.end()

        task = Task(task_id="task-1", action="test_action")
        with pytest.raises(RuntimeError):
            session.add_task(task)
