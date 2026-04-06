"""Test API runtime and handles"""

import pytest
from loom.api import (
    AgentRuntime,
    AgentProfile,
    SessionHandle,
    TaskHandle,
    RunHandle,
    RunState,
)


class TestRuntime:
    """Test AgentRuntime"""

    def test_runtime_creation(self):
        """Test runtime creation"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        assert runtime.profile.id == "default"

    def test_create_session(self):
        """Test create session"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        assert isinstance(session, SessionHandle)
        assert session.id

    def test_get_session(self):
        """Test get session"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        retrieved = runtime.get_session(session.id)
        assert retrieved.id == session.id


class TestSessionHandle:
    """Test SessionHandle"""

    def test_create_task(self):
        """Test create task"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        task = session.create_task(goal="Test")
        assert isinstance(task, TaskHandle)
        assert task.goal == "Test"

    def test_list_tasks(self):
        """Test list tasks"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        session.create_task(goal="Task 1")
        session.create_task(goal="Task 2")
        tasks = session.list_tasks()
        assert len(tasks) == 2

    def test_get_session_preserves_tasks(self):
        """Test session state survives handle recreation."""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        session.create_task(goal="Task 1")

        retrieved = runtime.get_session(session.id)
        tasks = retrieved.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].goal == "Task 1"


class TestTaskHandle:
    """Test TaskHandle"""

    def test_start_run(self):
        """Test start run"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        task = session.create_task(goal="Test")
        run = task.start()
        assert isinstance(run, RunHandle)
        assert run.state == RunState.QUEUED
