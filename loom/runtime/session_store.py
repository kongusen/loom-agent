"""Session storage contracts for Loom runtime state."""

from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SessionRecord:
    """Serializable session metadata snapshot."""

    id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class RunRecord:
    """Serializable completed-run snapshot."""

    id: str
    session_id: str
    state: str
    output: str = ""
    error: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TranscriptRecord:
    """Serializable execution transcript for session restoration."""

    id: str
    session_id: str
    prompt: str
    output: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionStore(ABC):
    """Pluggable store for session and run snapshots."""

    @abstractmethod
    def load_session(self, session_id: str) -> SessionRecord | None:
        """Return a session snapshot if it exists."""

    @abstractmethod
    def save_session(self, record: SessionRecord) -> None:
        """Persist a session snapshot."""

    @abstractmethod
    def save_run(self, record: RunRecord) -> None:
        """Persist a completed run snapshot."""

    def load_run(self, run_id: str) -> RunRecord | None:
        """Return a completed-run snapshot if supported."""
        _ = run_id
        return None

    def list_runs(self, session_id: str | None = None) -> list[RunRecord]:
        """Return completed-run snapshots if supported."""
        _ = session_id
        return []

    def save_transcript(self, record: TranscriptRecord) -> None:
        """Persist an execution transcript if supported."""
        _ = record

    def load_transcript(self, run_id: str) -> TranscriptRecord | None:
        """Return an execution transcript if supported."""
        _ = run_id
        return None

    def list_transcripts(self, session_id: str | None = None) -> list[TranscriptRecord]:
        """Return execution transcripts if supported."""
        _ = session_id
        return []

    def delete_session(self, session_id: str) -> None:
        """Delete a session snapshot if supported."""
        _ = session_id


class InMemorySessionStore(SessionStore):
    """Process-local session store useful for tests and embedding."""

    def __init__(self) -> None:
        self.sessions: dict[str, SessionRecord] = {}
        self.runs: dict[str, RunRecord] = {}
        self.transcripts: dict[str, TranscriptRecord] = {}

    def load_session(self, session_id: str) -> SessionRecord | None:
        return self.sessions.get(session_id)

    def save_session(self, record: SessionRecord) -> None:
        self.sessions[record.id] = record

    def save_run(self, record: RunRecord) -> None:
        self.runs[record.id] = record

    def load_run(self, run_id: str) -> RunRecord | None:
        return self.runs.get(run_id)

    def list_runs(self, session_id: str | None = None) -> list[RunRecord]:
        runs = list(self.runs.values())
        if session_id is None:
            return runs
        return [run for run in runs if run.session_id == session_id]

    def save_transcript(self, record: TranscriptRecord) -> None:
        self.transcripts[record.id] = record

    def load_transcript(self, run_id: str) -> TranscriptRecord | None:
        return self.transcripts.get(run_id)

    def list_transcripts(self, session_id: str | None = None) -> list[TranscriptRecord]:
        transcripts = list(self.transcripts.values())
        if session_id is None:
            return transcripts
        return [record for record in transcripts if record.session_id == session_id]

    def delete_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)
        self.runs = {
            run_id: run for run_id, run in self.runs.items() if run.session_id != session_id
        }
        self.transcripts = {
            run_id: transcript
            for run_id, transcript in self.transcripts.items()
            if transcript.session_id != session_id
        }


class FileSessionStore(SessionStore):
    """JSON-file backed session store for local apps and prototypes.

    This store persists session and completed-run snapshots across process
    restarts.  It intentionally stores plain metadata and run summaries; it is
    not a transcript database.
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        create_dirs: bool = True,
    ) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        if create_dirs:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_data(self._empty_data())

    def load_session(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            raw = self._read_data()["sessions"].get(session_id)
        if raw is None:
            return None
        return _session_record_from_json(raw)

    def save_session(self, record: SessionRecord) -> None:
        with self._lock:
            data = self._read_data()
            data["sessions"][record.id] = _session_record_to_json(record)
            self._write_data(data)

    def save_run(self, record: RunRecord) -> None:
        with self._lock:
            data = self._read_data()
            data["runs"][record.id] = _run_record_to_json(record)
            self._write_data(data)

    def load_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            raw = self._read_data()["runs"].get(run_id)
        if raw is None:
            return None
        return _run_record_from_json(raw)

    def list_runs(self, session_id: str | None = None) -> list[RunRecord]:
        with self._lock:
            raw_runs = list(self._read_data()["runs"].values())
        runs = [_run_record_from_json(raw) for raw in raw_runs]
        if session_id is None:
            return runs
        return [run for run in runs if run.session_id == session_id]

    def save_transcript(self, record: TranscriptRecord) -> None:
        with self._lock:
            data = self._read_data()
            data["transcripts"][record.id] = _transcript_record_to_json(record)
            self._write_data(data)

    def load_transcript(self, run_id: str) -> TranscriptRecord | None:
        with self._lock:
            raw = self._read_data()["transcripts"].get(run_id)
        if raw is None:
            return None
        return _transcript_record_from_json(raw)

    def list_transcripts(self, session_id: str | None = None) -> list[TranscriptRecord]:
        with self._lock:
            raw_transcripts = list(self._read_data()["transcripts"].values())
        transcripts = [_transcript_record_from_json(raw) for raw in raw_transcripts]
        if session_id is None:
            return transcripts
        return [record for record in transcripts if record.session_id == session_id]

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            data = self._read_data()
            data["sessions"].pop(session_id, None)
            data["runs"] = {
                run_id: run
                for run_id, run in data["runs"].items()
                if run.get("session_id") != session_id
            }
            data["transcripts"] = {
                run_id: transcript
                for run_id, transcript in data["transcripts"].items()
                if transcript.get("session_id") != session_id
            }
            self._write_data(data)

    def _read_data(self) -> dict[str, dict[str, Any]]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return self._empty_data()
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid session store JSON at {self.path}") from exc

        sessions = raw.get("sessions", {})
        runs = raw.get("runs", {})
        transcripts = raw.get("transcripts", {})
        if (
            not isinstance(sessions, dict)
            or not isinstance(runs, dict)
            or not isinstance(transcripts, dict)
        ):
            raise ValueError(f"invalid session store shape at {self.path}")
        return {"sessions": sessions, "runs": runs, "transcripts": transcripts}

    def _write_data(self, data: dict[str, dict[str, Any]]) -> None:
        payload = json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True, default=str)
        tmp_path = self.path.with_name(f"{self.path.name}.tmp")
        tmp_path.write_text(f"{payload}\n", encoding="utf-8")
        tmp_path.replace(self.path)

    def _empty_data(self) -> dict[str, dict[str, Any]]:
        return {"sessions": {}, "runs": {}, "transcripts": {}}


def _session_record_to_json(record: SessionRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "metadata": record.metadata,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _session_record_from_json(raw: dict[str, Any]) -> SessionRecord:
    return SessionRecord(
        id=str(raw["id"]),
        metadata=dict(raw.get("metadata", {})),
        created_at=_parse_datetime(raw.get("created_at")),
        updated_at=_parse_datetime(raw.get("updated_at")),
    )


def _run_record_to_json(record: RunRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "session_id": record.session_id,
        "state": record.state,
        "output": record.output,
        "error": record.error,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "metadata": record.metadata,
    }


def _run_record_from_json(raw: dict[str, Any]) -> RunRecord:
    error = raw.get("error")
    if error is not None and not isinstance(error, dict):
        logger.warning("Ignoring invalid run error payload for run %s", raw.get("id"))
        error = None
    return RunRecord(
        id=str(raw["id"]),
        session_id=str(raw["session_id"]),
        state=str(raw["state"]),
        output=str(raw.get("output", "")),
        error=error,
        created_at=_parse_datetime(raw.get("created_at")),
        updated_at=_parse_datetime(raw.get("updated_at")),
        metadata=dict(raw.get("metadata", {})),
    )


def _transcript_record_to_json(record: TranscriptRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "session_id": record.session_id,
        "prompt": record.prompt,
        "output": record.output,
        "messages": record.messages,
        "context": record.context,
        "events": record.events,
        "artifacts": record.artifacts,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "metadata": record.metadata,
    }


def _transcript_record_from_json(raw: dict[str, Any]) -> TranscriptRecord:
    messages = raw.get("messages", [])
    events = raw.get("events", [])
    artifacts = raw.get("artifacts", [])
    return TranscriptRecord(
        id=str(raw["id"]),
        session_id=str(raw["session_id"]),
        prompt=str(raw.get("prompt", "")),
        output=str(raw.get("output", "")),
        messages=list(messages) if isinstance(messages, list) else [],
        context=dict(raw.get("context", {})),
        events=list(events) if isinstance(events, list) else [],
        artifacts=list(artifacts) if isinstance(artifacts, list) else [],
        created_at=_parse_datetime(raw.get("created_at")),
        updated_at=_parse_datetime(raw.get("updated_at")),
        metadata=dict(raw.get("metadata", {})),
    )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            logger.warning("Invalid datetime in session store: %s", value)
    return datetime.now()
