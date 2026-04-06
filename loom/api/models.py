"""Runtime models for Loom framework

Core objects: Session, Task, Run, Event, Approval, Artifact
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def generate_id() -> str:
    """Generate unique ID"""
    return str(uuid4())


class RunState(Enum):
    """Run execution state"""
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_EXTERNAL = "waiting_external"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    BLOCKED_BY_CAPABILITY = "blocked_by_capability"


class TrustTier(Enum):
    """Knowledge source trust level"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Session:
    """Persistent interaction context"""
    id: str = field(default_factory=generate_id)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Internal state (not serialized)
    _agent_core: Any = field(default=None, repr=False)
    _context: Any = field(default=None, repr=False)
    _tasks: dict[str, Any] = field(default_factory=dict, repr=False)
    _closed: bool = field(default=False, repr=False)


@dataclass
class Task:
    """Executable goal unit"""
    id: str = field(default_factory=generate_id)
    session_id: str = ""
    goal: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    _runs: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class Run:
    """Single execution of a task"""
    id: str = field(default_factory=generate_id)
    task_id: str = ""
    state: RunState = RunState.QUEUED
    goal: str = ""
    current_step: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    summary: str = ""
    pending_approval_id: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    _events: list[Any] = field(default_factory=list, repr=False)
    _artifacts: list[Any] = field(default_factory=list, repr=False)
    _approvals: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class Event:
    """Structured event during run"""
    event_id: str = field(default_factory=generate_id)
    run_id: str = ""
    type: str = ""
    ts: datetime = field(default_factory=datetime.now)
    visibility: str = "user"  # user, system, audit
    correlation_id: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Approval:
    """Human-in-the-loop approval node"""
    approval_id: str = field(default_factory=generate_id)
    run_id: str = ""
    kind: str = ""  # tool_execution, policy_override, external_publish
    status: str = "pending"  # pending, approved, rejected, expired
    question: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    timeout_seconds: int = 600


@dataclass
class Artifact:
    """Execution output"""
    artifact_id: str = field(default_factory=generate_id)
    run_id: str = ""
    kind: str = ""  # patch, report, json, text, evidence_pack
    title: str = ""
    uri: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Citation:
    """Knowledge source citation"""
    citation_id: str = field(default_factory=generate_id)
    source_id: str = ""
    title: str = ""
    uri: str = ""
    excerpt: str = ""
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EvidenceItem:
    """Single evidence item"""
    item_id: str = field(default_factory=generate_id)
    content: str = ""
    citations: list[Citation] = field(default_factory=list)
    relevance_score: float = 0.0


@dataclass
class EvidencePack:
    """Evidence package - RAG as Evidence, not Memory"""
    pack_id: str = field(default_factory=generate_id)
    run_id: str = ""
    question: str = ""
    summary: str = ""
    items: list[EvidenceItem] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0
    freshness: datetime = field(default_factory=datetime.now)
    sources_used: list[str] = field(default_factory=list)


@dataclass
class KnowledgeQuery:
    """Knowledge search query"""
    query_id: str = field(default_factory=generate_id)
    run_id: str = ""
    question: str = ""
    sources: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    max_results: int = 10


@dataclass
class ActiveQuestion:
    """Active question being resolved"""
    question_id: str = field(default_factory=generate_id)
    run_id: str = ""
    question: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    evidence_pack_id: Optional[str] = None


@dataclass
class ResumePoint:
    """Run resume checkpoint"""
    run_id: str = ""
    step_index: int = 0
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    pending_tool_calls: list[Any] = field(default_factory=list)
    pending_approvals: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RunResult:
    """Run execution result"""
    run_id: str = ""
    state: RunState = RunState.COMPLETED
    summary: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    error: Optional[dict[str, Any]] = None
    duration_ms: int = 0
