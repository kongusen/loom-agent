"""Dashboard - never compressed working state"""

from ..types import Dashboard as DashboardType


class DashboardManager:
    """Manage Dashboard state"""

    def __init__(self, dashboard: DashboardType | None = None):
        self.dashboard = dashboard or DashboardType()

    def bind(self, dashboard: DashboardType) -> DashboardType:
        """Bind manager to a live working dashboard."""
        self.dashboard = dashboard
        return self.dashboard

    def update_rho(self, rho: float):
        """Update context pressure"""
        self.dashboard.rho = rho

    def update_token_budget(self, token_budget: int):
        """Update remaining token budget."""
        self.dashboard.token_budget = token_budget

    def update_progress(self, progress: str):
        """Update goal progress"""
        self.dashboard.goal_progress = progress

    def set_plan(self, plan: list[str]):
        """Replace current plan."""
        self.dashboard.plan = list(plan)

    def set_scratchpad(self, scratchpad: str):
        """Replace scratchpad content."""
        self.dashboard.scratchpad = scratchpad

    def add_pending_event(self, event: dict):
        """Add event to pending_events"""
        event_id = event.get("event_id")
        if event_id and any(
            existing.get("event_id") == event_id
            for existing in self.dashboard.event_surface.pending_events
        ):
            return
        self.dashboard.event_surface.pending_events.append(event)

    def acknowledge_event(self, event_id: str, decision: dict):
        """Acknowledge event and move to recent_event_decisions"""
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
        self.dashboard.event_surface.active_risks.append(risk)

    def add_question(self, question: str):
        """Add active question to knowledge_surface"""
        if question in self.dashboard.knowledge_surface.active_questions:
            return
        self.dashboard.knowledge_surface.active_questions.append(question)

    def add_evidence(self, evidence: dict):
        """Add evidence pack to knowledge_surface"""
        self.dashboard.knowledge_surface.evidence_packs.append(evidence)
        citation = evidence.get("citation") or evidence.get("source")
        if citation and citation not in self.dashboard.knowledge_surface.citations:
            self.dashboard.knowledge_surface.citations.append(str(citation))

    def increment_errors(self):
        """Increment error count"""
        self.dashboard.error_count += 1

    def update_heartbeat(self, timestamp: str):
        """Update last heartbeat timestamp"""
        self.dashboard.last_hb_ts = timestamp

    def request_interrupt(self):
        """Request interrupt from heartbeat"""
        self.dashboard.interrupt_requested = True

    def ingest_heartbeat_event(self, event: dict, urgency: str):
        """Project a heartbeat event into dashboard state."""
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
        return {
            "rho": self.dashboard.rho,
            "interrupt_requested": self.dashboard.interrupt_requested,
            "error_count": self.dashboard.error_count,
            "pending_events": len(self.dashboard.event_surface.pending_events),
            "active_risks": len(self.dashboard.event_surface.active_risks),
            "active_questions": len(self.dashboard.knowledge_surface.active_questions),
            "goal_progress": self.dashboard.goal_progress,
        }
