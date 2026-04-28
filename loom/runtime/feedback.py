"""Runtime feedback policy contracts.

Feedback is **read-only observation** of runtime events.  Feedback policies
record what happened (tool results, LLM outputs, context operations) but never
modify, block, or influence the execution flow.

For **control-plane** decisions — vetoing tool calls, requesting human
confirmation, or enforcing governance rules — use hooks
(``agent.on("before_*", ...)``) or ``GovernancePolicy``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class FeedbackEvent:
    """Normalized runtime feedback event."""

    type: str
    source: str = "runtime"
    payload: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    session_id: str | None = None
    iteration: int | None = None
    success: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FeedbackDecision:
    """Decision returned after a feedback policy receives an event."""

    accepted: bool
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeFeedbackPolicy(Protocol):
    """Protocol implemented by runtime feedback policies."""

    def attach(self, engine: Any) -> None: ...

    def record(self, event: FeedbackEvent) -> FeedbackDecision: ...

    def get_feedback(self) -> list[dict[str, Any]]: ...


class FeedbackPolicy:
    """Factory for built-in runtime feedback policies."""

    @staticmethod
    def none() -> NoopFeedbackPolicy:
        return NoopFeedbackPolicy()

    @staticmethod
    def collector(loop: Any | None = None) -> CollectingFeedbackPolicy:
        return CollectingFeedbackPolicy(loop=loop)

    @staticmethod
    def evolution(evolution_engine: Any | None = None) -> EvolutionFeedbackPolicy:
        return EvolutionFeedbackPolicy(evolution_engine=evolution_engine)


class NoopFeedbackPolicy:
    """Feedback policy for applications that do not collect runtime feedback."""

    def attach(self, engine: Any) -> None:
        _ = engine

    def record(self, event: FeedbackEvent) -> FeedbackDecision:
        _ = event
        return FeedbackDecision(accepted=False, reason="feedback disabled")

    def get_feedback(self) -> list[dict[str, Any]]:
        return []


class CollectingFeedbackPolicy:
    """Feedback policy that records selected runtime events into a feedback loop."""

    def __init__(self, loop: Any | None = None) -> None:
        if loop is None:
            from ..evolution.feedback import FeedbackLoop

            loop = FeedbackLoop()
        self.loop = loop
        self._attached_engines: set[int] = set()

    def attach(self, engine: Any) -> None:
        subscribe = getattr(engine, "on", None)
        if not callable(subscribe):
            raise TypeError("engine does not support event subscription")

        engine_id = id(engine)
        if engine_id in self._attached_engines:
            return
        self._attached_engines.add(engine_id)

        for event_name in (
            "tool_result",
            "after_llm",
            "on_context_compact",
            "context_renewed",
            "signal_decided",
        ):
            subscribe(event_name, self._make_handler(event_name))

    def record(self, event: FeedbackEvent) -> FeedbackDecision:
        entry = self._entry_from_event(event)
        add_feedback = getattr(self.loop, "add_feedback", None)
        if not callable(add_feedback):
            raise TypeError("feedback loop does not support add_feedback()")
        add_feedback(entry)
        return FeedbackDecision(
            accepted=True,
            metadata={"type": event.type, "source": event.source},
        )

    def get_feedback(self) -> list[dict[str, Any]]:
        getter = getattr(self.loop, "get_feedback", None)
        if not callable(getter):
            return []
        feedback = getter()
        if not isinstance(feedback, list):
            return []
        return [item for item in feedback if isinstance(item, dict)]

    def _make_handler(self, event_name: str):
        def _handler(**payload: Any) -> None:
            self.record(self._event_from_payload(event_name, payload))

        return _handler

    def _event_from_payload(
        self,
        event_name: str,
        payload: dict[str, Any],
    ) -> FeedbackEvent:
        success = payload.get("success")
        return FeedbackEvent(
            type=event_name,
            payload=dict(payload),
            iteration=_int_or_none(payload.get("iteration")),
            success=success if isinstance(success, bool) else None,
        )

    def _entry_from_event(self, event: FeedbackEvent) -> dict[str, Any]:
        payload = dict(event.payload)
        entry: dict[str, Any] = {
            "event_type": event.type,
            "type": event.type,
            "source": event.source,
            "payload": payload,
            "metadata": dict(event.metadata),
        }
        if event.run_id is not None:
            entry["run_id"] = event.run_id
        if event.session_id is not None:
            entry["session_id"] = event.session_id
        if event.iteration is not None:
            entry["iteration"] = event.iteration
        if event.success is not None:
            entry["success"] = event.success

        if event.type == "tool_result":
            return self._tool_result_entry(event, entry)
        return entry

    def _tool_result_entry(
        self,
        event: FeedbackEvent,
        entry: dict[str, Any],
    ) -> dict[str, Any]:
        payload = event.payload
        tool_name = payload.get("tool_name") or payload.get("tool") or payload.get("name")
        success = event.success
        if success is None and isinstance(payload.get("success"), bool):
            success = payload["success"]
        if success is None:
            success = True

        entry.update(
            {
                "tool": tool_name,
                "tool_name": tool_name,
                "tool_call_id": payload.get("tool_call_id"),
                "type": "success" if success else "failure",
                "success": success,
                "result": payload.get("result"),
            }
        )
        return entry


class EvolutionFeedbackPolicy(CollectingFeedbackPolicy):
    """Feedback policy that feeds runtime feedback into an EvolutionEngine."""

    def __init__(self, evolution_engine: Any | None = None) -> None:
        if evolution_engine is None:
            from ..evolution.engine import EvolutionEngine

            evolution_engine = EvolutionEngine()
        self.evolution_engine = evolution_engine
        super().__init__(loop=evolution_engine.feedback_loop)

    def evolve(self, agent: Any) -> None:
        self.evolution_engine.evolve(agent)


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None
