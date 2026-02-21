"""Session context — Python equivalent of Node.js AsyncLocalStorage."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from .events import EventBus
from .memory import MemoryManager


@dataclass
class SessionContext:
    tenant_id: str
    user_id: str
    session_id: str
    memory: MemoryManager
    events: EventBus


_current_session: ContextVar[SessionContext | None] = ContextVar("_current_session", default=None)


def get_current_session() -> SessionContext:
    ctx = _current_session.get()
    if ctx is None:
        raise RuntimeError("No active session")
    return ctx


def set_session(session: SessionContext) -> Any:
    return _current_session.set(session)


def reset_session(token: Any) -> None:
    _current_session.reset(token)


@contextmanager
def run_in_session(session: SessionContext) -> Generator[SessionContext, None, None]:
    token = set_session(session)
    try:
        yield session
    finally:
        reset_session(token)
