"""Signal coordination runtime extracted from AgentEngine internals."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, cast

from .signals import AttentionPolicy, RuntimeSignal, SignalDecision, SignalQueue, coerce_signal

logger = logging.getLogger(__name__)


class SignalRuntime:
    """Owns runtime signal ingestion, decisioning, and dispatch."""

    def __init__(
        self,
        *,
        context_manager: Any,
        emit: Callable[[str], None],
        attention_policy: AttentionPolicy | None = None,
        signal_queue: SignalQueue | None = None,
    ) -> None:
        self.context_manager = context_manager
        self.emit = emit
        self.attention_policy = attention_policy or AttentionPolicy()
        self.signal_queue = signal_queue or SignalQueue()

    def ingest_signal(
        self,
        signal: RuntimeSignal | str,
        *,
        source: str = "custom",
        type: str = "event",
        urgency: str = "normal",
        payload: dict[str, Any] | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        dedupe_key: str | None = None,
    ) -> SignalDecision:
        normalized = coerce_signal(
            signal,
            source=source,
            type=type,
            urgency=cast("Any", urgency),
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            dedupe_key=dedupe_key,
        )
        self.emit("signal_received", signal=normalized)
        self.signal_queue.push(normalized)
        decision = self.attention_policy.decide(
            normalized,
            state=self.context_manager.dashboard.decision_state(),
        )
        self.emit("signal_decided", signal=normalized, decision=decision)
        return decision

    def drain_signals(self) -> list[tuple[RuntimeSignal, SignalDecision]]:
        drained: list[tuple[RuntimeSignal, SignalDecision]] = []
        for signal in self.signal_queue.drain():
            decision = self.attention_policy.decide(
                signal,
                state=self.context_manager.dashboard.decision_state(),
            )
            self.context_manager.ingest_signal(signal, decision)
            self.emit("signal_dispatched", signal=signal, decision=decision)
            drained.append((signal, decision))
        return drained

    def handle_heartbeat_event(self, event: dict[str, Any], urgency: str) -> SignalDecision:
        logger.info("Heartbeat event (%s): %s", urgency, event)
        summary = str(event.get("summary") or event.get("type") or "Heartbeat event")
        signal = RuntimeSignal.create(
            summary,
            source=str(event.get("source") or "heartbeat"),
            type=str(event.get("type") or "event"),
            urgency=cast("Any", urgency),
            payload=dict(event),
            dedupe_key=event.get("event_id"),
        )
        return self.ingest_signal(signal)
