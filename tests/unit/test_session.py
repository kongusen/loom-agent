"""Unit tests for session context module."""

import pytest
from loom.session import SessionContext, get_current_session, set_session, reset_session, run_in_session
from loom.memory import MemoryManager
from loom.events import EventBus


def _make_session():
    return SessionContext(tenant_id="t1", user_id="u1", session_id="s1", memory=MemoryManager(), events=EventBus())


class TestSessionContext:
    def test_get_raises_without_session(self):
        with pytest.raises(RuntimeError, match="No active session"):
            get_current_session()

    def test_set_and_get(self):
        s = _make_session()
        token = set_session(s)
        try:
            assert get_current_session() is s
        finally:
            reset_session(token)

    def test_reset_restores_previous(self):
        s1 = _make_session()
        s2 = _make_session()
        t1 = set_session(s1)
        t2 = set_session(s2)
        assert get_current_session() is s2
        reset_session(t2)
        assert get_current_session() is s1
        reset_session(t1)

    def test_run_in_session_context_manager(self):
        s = _make_session()
        with run_in_session(s) as ctx:
            assert ctx is s
            assert get_current_session() is s
        with pytest.raises(RuntimeError):
            get_current_session()

    def test_run_in_session_restores_on_exception(self):
        s = _make_session()
        with pytest.raises(ValueError):
            with run_in_session(s):
                raise ValueError("boom")
        with pytest.raises(RuntimeError):
            get_current_session()
