"""Test API models"""

import pytest
from datetime import datetime
from loom.api import (
    Session,
    Task,
    Run,
    Event,
    Approval,
    Artifact,
    RunState,
    RunResult,
    Citation,
    EvidencePack,
    generate_id,
)


class TestModels:
    """Test core models"""

    def test_session_creation(self):
        """Test Session creation"""
        session = Session()
        assert session.id
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.metadata, dict)

    def test_task_creation(self):
        """Test Task creation"""
        task = Task(session_id="sess_001", goal="Test goal")
        assert task.id
        assert task.session_id == "sess_001"
        assert task.goal == "Test goal"

    def test_run_creation(self):
        """Test Run creation"""
        run = Run(task_id="task_001", goal="Test")
        assert run.id
        assert run.state == RunState.QUEUED
        assert run.current_step == 0

    def test_run_state_enum(self):
        """Test RunState enum"""
        assert RunState.QUEUED.value == "queued"
        assert RunState.RUNNING.value == "running"
        assert RunState.COMPLETED.value == "completed"

    def test_event_creation(self):
        """Test Event creation"""
        event = Event(
            run_id="run_001",
            type="tool.started",
            visibility="user"
        )
        assert event.event_id
        assert event.type == "tool.started"
        assert event.visibility == "user"

    def test_approval_creation(self):
        """Test Approval creation"""
        approval = Approval(
            run_id="run_001",
            kind="tool_execution",
            question="Allow?"
        )
        assert approval.approval_id
        assert approval.status == "pending"
        assert approval.timeout_seconds == 600

    def test_artifact_creation(self):
        """Test Artifact creation"""
        artifact = Artifact(
            run_id="run_001",
            kind="patch",
            title="Fix"
        )
        assert artifact.artifact_id
        assert artifact.kind == "patch"

    def test_citation_creation(self):
        """Test Citation creation"""
        citation = Citation(
            source_id="docs",
            title="Python Docs",
            uri="https://docs.python.org",
            excerpt="Example"
        )
        assert citation.citation_id
        assert citation.confidence == 0.0

    def test_evidence_pack_creation(self):
        """Test EvidencePack creation"""
        pack = EvidencePack(
            run_id="run_001",
            question="How to?",
            summary="Summary"
        )
        assert pack.pack_id
        assert isinstance(pack.citations, list)

    def test_run_result_creation(self):
        """Test RunResult creation"""
        result = RunResult(
            run_id="run_001",
            state=RunState.COMPLETED,
            summary="Done"
        )
        assert result.state == RunState.COMPLETED
        assert isinstance(result.artifacts, list)

    def test_generate_id(self):
        """Test ID generation"""
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) > 0
