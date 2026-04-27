"""Runtime signal contracts for external agent inputs."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import uuid4

SignalUrgency = Literal["low", "normal", "high", "critical"]
SignalAction = Literal[
    "ignore",
    "observe",
    "queue",
    "run",
    "interrupt",
    "interrupt_now",
]
SignalStringField = str | Callable[[Any], str | None] | None
SignalPayloadField = (
    Mapping[str, Any]
    | Callable[[Any], Mapping[str, Any] | None]
    | None
)


@dataclass(slots=True)
class RuntimeSignal:
    """A normalized runtime input from any producer.

    Gateway, heartbeat, cron, and application events should all be converted
    into this shape before they enter the agent runtime.
    """

    id: str = field(default_factory=lambda: f"sig_{uuid4().hex}")
    source: str = "custom"
    type: str = "event"
    summary: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    urgency: SignalUrgency = "normal"
    session_id: str | None = None
    run_id: str | None = None
    dedupe_key: str | None = None
    observed_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        content: str,
        *,
        source: str = "custom",
        type: str = "event",
        urgency: SignalUrgency = "normal",
        payload: dict[str, Any] | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        dedupe_key: str | None = None,
    ) -> RuntimeSignal:
        data = dict(payload or {})
        data.setdefault("content", content)
        return cls(
            source=source,
            type=type,
            summary=content,
            payload=data,
            urgency=urgency,
            session_id=session_id,
            run_id=run_id,
            dedupe_key=dedupe_key,
        )

    def for_session(self, session_id: str) -> RuntimeSignal:
        """Return a copy associated with a session when one is missing."""
        if self.session_id == session_id:
            return self
        return replace(self, session_id=session_id)

    def for_run(self, run_id: str) -> RuntimeSignal:
        """Return a copy associated with a run when one is missing."""
        if self.run_id == run_id:
            return self
        return replace(self, run_id=run_id)

    def to_event(self) -> dict[str, Any]:
        """Serialize to the dashboard event surface shape."""
        return {
            "event_id": self.id,
            "source": self.source,
            "type": self.type,
            "summary": self.summary,
            "urgency": self.urgency,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "dedupe_key": self.dedupe_key,
            "observed_at": self.observed_at.isoformat(),
            "payload": dict(self.payload),
        }


class RuntimeSignalAdapter(Protocol):
    """Protocol for objects that normalize external events into runtime signals."""

    def adapt(self, event: Any) -> RuntimeSignal:
        ...


@dataclass(slots=True)
class SignalAdapter:
    """Small adapter from application events to ``RuntimeSignal``.

    This is intentionally producer-agnostic. A Slack message, cron tick,
    heartbeat alert, webhook, or dashboard callback can all use the same shape:
    the adapter labels the source and extracts summary/payload fields, while the
    runtime only sees a normalized ``RuntimeSignal``.
    """

    source: str
    type: str = "event"
    urgency: SignalUrgency = "normal"
    summary: SignalStringField = None
    payload: SignalPayloadField = None
    session_id: SignalStringField = None
    run_id: SignalStringField = None
    dedupe_key: SignalStringField = None

    def adapt(self, event: Any) -> RuntimeSignal:
        """Convert one external event into a runtime signal."""
        if isinstance(event, RuntimeSignal):
            return event

        summary = _resolve_string(self.summary, event) or _default_summary(event)
        payload = _resolve_payload(self.payload, event)
        session_id = _resolve_string(self.session_id, event)
        run_id = _resolve_string(self.run_id, event)
        dedupe_key = _resolve_string(self.dedupe_key, event)

        return RuntimeSignal.create(
            summary,
            source=self.source,
            type=self.type,
            urgency=self.urgency,
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            dedupe_key=dedupe_key,
        )


@dataclass(slots=True)
class SignalDecision:
    """Attention policy outcome for one signal."""

    action: SignalAction
    reason: str = ""

    def to_event(self, signal: RuntimeSignal) -> dict[str, Any]:
        return {
            "event_id": signal.id,
            "action": self.action,
            "reason": self.reason,
            "source": signal.source,
            "type": signal.type,
            "urgency": signal.urgency,
            "observed_at": signal.observed_at.isoformat(),
        }


@dataclass(slots=True)
class AttentionPolicy:
    """Default signal attention policy.

    The policy intentionally ignores producer names. It only looks at the
    normalized signal and optional runtime state.
    """

    low: SignalAction = "observe"
    normal: SignalAction = "run"
    high: SignalAction = "interrupt"
    critical: SignalAction = "interrupt_now"

    def decide(
        self,
        signal: RuntimeSignal,
        state: dict[str, Any] | None = None,
    ) -> SignalDecision:
        _ = state
        action = {
            "low": self.low,
            "normal": self.normal,
            "high": self.high,
            "critical": self.critical,
        }.get(signal.urgency, self.normal)
        return SignalDecision(action=action, reason=f"urgency:{signal.urgency}")


class SignalQueue:
    """Thread-safe in-memory queue with basic dedupe."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._signals: list[RuntimeSignal] = []
        self._dedupe_keys: set[str] = set()

    def push(self, signal: RuntimeSignal) -> bool:
        with self._lock:
            key = signal.dedupe_key
            if key and key in self._dedupe_keys:
                return False
            self._signals.append(signal)
            if key:
                self._dedupe_keys.add(key)
            return True

    def extend(self, signals: Iterable[RuntimeSignal]) -> int:
        count = 0
        for signal in signals:
            if self.push(signal):
                count += 1
        return count

    def drain(self) -> list[RuntimeSignal]:
        with self._lock:
            signals = self._signals
            self._signals = []
            return signals

    def __len__(self) -> int:
        with self._lock:
            return len(self._signals)


def coerce_signal(
    signal: RuntimeSignal | str,
    *,
    source: str = "custom",
    type: str = "event",
    urgency: SignalUrgency = "normal",
    payload: dict[str, Any] | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    dedupe_key: str | None = None,
) -> RuntimeSignal:
    """Normalize public signal input."""
    if isinstance(signal, RuntimeSignal):
        result = signal
        if session_id is not None and result.session_id != session_id:
            result = replace(result, session_id=session_id)
        if run_id is not None and result.run_id != run_id:
            result = replace(result, run_id=run_id)
        return result
    if not isinstance(signal, str):
        raise TypeError(f"signal must be RuntimeSignal or str, got {type(signal).__name__}")
    return RuntimeSignal.create(
        signal,
        source=source,
        type=type,
        urgency=urgency,
        payload=payload,
        session_id=session_id,
        run_id=run_id,
        dedupe_key=dedupe_key,
    )


def adapt_signal(
    event: RuntimeSignal | str | Any,
    *,
    adapter: RuntimeSignalAdapter | None = None,
    source: str | None = None,
    type: str | None = None,
    urgency: SignalUrgency | None = None,
    payload: dict[str, Any] | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    dedupe_key: str | None = None,
) -> RuntimeSignal:
    """Normalize public signal or adapter input."""
    if adapter is not None:
        signal = adapter.adapt(event)
        return _override_signal(
            signal,
            source=source,
            type=type,
            urgency=urgency,
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            dedupe_key=dedupe_key,
        )
    return coerce_signal(
        event,
        source=source or "custom",
        type=type or "event",
        urgency=urgency or "normal",
        payload=payload,
        session_id=session_id,
        run_id=run_id,
        dedupe_key=dedupe_key,
    )


def _override_signal(
    signal: RuntimeSignal,
    *,
    source: str | None = None,
    type: str | None = None,
    urgency: SignalUrgency | None = None,
    payload: dict[str, Any] | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    dedupe_key: str | None = None,
) -> RuntimeSignal:
    return replace(
        signal,
        source=source if source is not None else signal.source,
        type=type if type is not None else signal.type,
        urgency=urgency if urgency is not None else signal.urgency,
        payload=dict(payload) if payload is not None else signal.payload,
        session_id=session_id if session_id is not None else signal.session_id,
        run_id=run_id if run_id is not None else signal.run_id,
        dedupe_key=dedupe_key if dedupe_key is not None else signal.dedupe_key,
    )


def _resolve_string(field: SignalStringField, event: Any) -> str | None:
    if field is None:
        return None
    value = field(event) if callable(field) else field
    if value is None:
        return None
    return str(value)


def _resolve_payload(field: SignalPayloadField, event: Any) -> dict[str, Any]:
    if callable(field):
        value = field(event)
        return dict(value or {})
    if field is not None:
        return dict(field)
    if isinstance(event, Mapping):
        return dict(event)
    return {"event": event}


def _default_summary(event: Any) -> str:
    if isinstance(event, str):
        return event
    if isinstance(event, Mapping):
        for key in ("summary", "content", "text", "message", "name", "id"):
            value = event.get(key)
            if value is not None:
                return str(value)
    return str(event)
