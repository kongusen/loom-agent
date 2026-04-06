"""Agent Runtime - main entry point"""

from typing import Optional
from .models import Session, generate_id
from .profile import AgentProfile
from .handles import SessionHandle
from .events import EventBus
from .artifacts import ArtifactStore
from ..providers.base import LLMProvider


class AgentRuntime:
    """Agent Runtime Framework entry point"""

    def __init__(
        self,
        profile: AgentProfile,
        provider: LLMProvider | None = None,
        event_bus: EventBus | None = None,
        artifact_store: ArtifactStore | None = None,
    ):
        self.profile = profile
        self.provider = provider
        self.sessions: dict[str, Session] = {}
        self.event_bus = event_bus or EventBus()
        self.artifact_store = artifact_store or ArtifactStore()

    def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> SessionHandle:
        """Create a new session"""
        session = Session(
            id=session_id or generate_id(),
            metadata=metadata or {}
        )
        self.sessions[session.id] = session
        return SessionHandle(session, self)

    def get_session(self, session_id: str) -> Optional[SessionHandle]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        return SessionHandle(session, self) if session else None

    def list_sessions(self) -> list[SessionHandle]:
        """List all sessions"""
        return [SessionHandle(s, self) for s in self.sessions.values()]
