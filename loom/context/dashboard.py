"""Dashboard - never compressed working state"""

import threading
from typing import Any

from ..types import Dashboard as DashboardType
from .event_aggregator import EventAggregator

_PENDING_EVENTS_AGGREGATE_THRESHOLD = 10


class DashboardManager:
    """Manage Dashboard state"""

    def __init__(
        self,
        dashboard: DashboardType | None = None,
        lock: Any = None,
    ):
        self.dashboard = dashboard or DashboardType()
        self._lock = lock or threading.RLock()
        self._aggregator = EventAggregator()

    def bind(self, dashboard: DashboardType) -> DashboardType:
        """Bind manager to a live working dashboard."""
        with self._lock:
            self.dashboard = dashboard
            return self.dashboard

    def update_rho(self, rho: float):
        """Update context pressure"""
        with self._lock:
            self.dashboard.rho = rho

    def update_token_budget(self, token_budget: int):
        """Update remaining token budget."""
        with self._lock:
            self.dashboard.token_budget = token_budget

    def update_progress(self, progress: str):
        """Update goal progress"""
        with self._lock:
            self.dashboard.goal_progress = progress

    def set_plan(self, plan: list[str]):
        """Replace current plan."""
        with self._lock:
            self.dashboard.plan = list(plan)

    def set_scratchpad(self, scratchpad: str):
        """Replace scratchpad content."""
        with self._lock:
            self.dashboard.scratchpad = scratchpad

    def add_pending_event(self, event: dict):
        """Add event to pending_events, aggregating when the list grows large."""
        with self._lock:
            event_id = event.get("event_id")
            if event_id and any(
                existing.get("event_id") == event_id
                for existing in self.dashboard.event_surface.pending_events
            ):
                return
            self.dashboard.event_surface.pending_events.append(event)
            if len(self.dashboard.event_surface.pending_events) >= _PENDING_EVENTS_AGGREGATE_THRESHOLD:
                self.dashboard.event_surface.pending_events = self._aggregator.aggregate(
                    self.dashboard.event_surface.pending_events
                )

    def acknowledge_event(self, event_id: str, decision: dict):
        """Acknowledge event and move to recent_event_decisions"""
        with self._lock:
            self.dashboard.event_surface.pending_events = [
                e for e in self.dashboard.event_surface.pending_events
                if e.get('event_id') != event_id
            ]
            self.dashboard.event_surface.active_risks = [
                risk for risk in self.dashboard.event_surface.active_risks
                if risk.get('event_id') != event_id
            ]
            if event_id and "event_id" not in decision:
                decision = {**decision, "event_id": event_id}
            self.dashboard.event_surface.recent_event_decisions.append(decision)
            self.dashboard.interrupt_requested = False

    def add_active_risk(self, risk: dict):
        """Add active risk"""
        with self._lock:
            self.dashboard.event_surface.active_risks.append(risk)

    def add_question(self, question: str):
        """Add active question to knowledge_surface"""
        with self._lock:
            if question in self.dashboard.knowledge_surface.active_questions:
                return
            self.dashboard.knowledge_surface.active_questions.append(question)

    def add_evidence(self, evidence: dict):
        """Add evidence pack to knowledge_surface"""
        with self._lock:
            self.dashboard.knowledge_surface.evidence_packs.append(evidence)
            citation = evidence.get("citation") or evidence.get("source")
            if citation and citation not in self.dashboard.knowledge_surface.citations:
                self.dashboard.knowledge_surface.citations.append(str(citation))

    def increment_errors(self):
        """Increment error count"""
        with self._lock:
            self.dashboard.error_count += 1

    def update_heartbeat(self, timestamp: str):
        """Update last heartbeat timestamp"""
        with self._lock:
            self.dashboard.last_hb_ts = timestamp

    def request_interrupt(self):
        """Request interrupt from heartbeat"""
        with self._lock:
            self.dashboard.interrupt_requested = True

    def ingest_heartbeat_event(self, event: dict, urgency: str):
        """Project a heartbeat event into dashboard state."""
        with self._lock:
            self.update_heartbeat(event.get("observed_at", ""))
            self.add_pending_event(event)
            if urgency in {"high", "critical"}:
                self.add_active_risk(
                    {
                        "event_id": event.get("event_id"),
                        "summary": event.get("summary", ""),
                        "urgency": urgency,
                    }
                )
                self.request_interrupt()

    def decision_state(self) -> dict:
        """Expose dashboard state that should influence runtime decisions."""
        with self._lock:
            return {
                "rho": self.dashboard.rho,
                "interrupt_requested": self.dashboard.interrupt_requested,
                "error_count": self.dashboard.error_count,
                "pending_events": len(self.dashboard.event_surface.pending_events),
                "active_risks": len(self.dashboard.event_surface.active_risks),
                "active_questions": len(self.dashboard.knowledge_surface.active_questions),
                "goal_progress": self.dashboard.goal_progress,
            }
