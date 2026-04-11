"""Test context extended modules - compression, renewal, event_aggregator, dashboard"""


import pytest

from loom.context.compression import CompressionPolicy, ContextCompressor
from loom.context.dashboard import DashboardManager
from loom.context.event_aggregator import EventAggregator
from loom.context.partitions import ContextPartitions
from loom.context.renewal import ContextRenewer
from loom.types import Dashboard, Message

# ── ContextCompressor ──

class TestContextCompressor:
    def test_creation(self):
        comp = ContextCompressor()
        assert comp.thresholds['snip'] == 0.7
        assert comp.thresholds['auto'] == 0.95

    def test_should_compress_none(self):
        comp = ContextCompressor()
        assert comp.should_compress(0.5) is None

    def test_should_compress_snip(self):
        comp = ContextCompressor()
        assert comp.should_compress(0.7) == 'snip'

    def test_should_compress_micro(self):
        comp = ContextCompressor()
        assert comp.should_compress(0.8) == 'micro'

    def test_should_compress_collapse(self):
        comp = ContextCompressor()
        assert comp.should_compress(0.9) == 'collapse'

    def test_should_compress_auto(self):
        comp = ContextCompressor()
        assert comp.should_compress(0.95) == 'auto'

    def test_should_compress_high(self):
        comp = ContextCompressor()
        assert comp.should_compress(1.0) == 'auto'

    def test_supports_custom_compression_policy(self):
        policy = CompressionPolicy(
            snip_at=0.6,
            micro_at=0.7,
            collapse_at=0.85,
            auto_compact_at=0.95,
        )
        comp = ContextCompressor(policy=policy)
        assert comp.thresholds["snip"] == 0.6
        assert comp.should_compress(0.72) == "micro"

    def test_rejects_non_monotonic_compression_policy(self):
        with pytest.raises(ValueError):
            CompressionPolicy(snip_at=0.8, micro_at=0.7)

    def test_snip_compact_short(self):
        comp = ContextCompressor()
        msgs = [Message(role="user", content="short")]
        result = comp.snip_compact(msgs)
        assert len(result) == 1
        assert result[0].content == "short"

    def test_snip_compact_long(self):
        comp = ContextCompressor()
        long_content = "a" * 3000
        msgs = [Message(role="user", content=long_content)]
        result = comp.snip_compact(msgs, max_length=2000)
        assert len(result) == 1
        assert len(result[0].content) < 3000
        assert "snipped" in result[0].content

    def test_micro_compact(self):
        comp = ContextCompressor()
        msgs = [
            Message(role="user", content="test"),
            Message(role="tool", content="ok", name="Read", tool_call_id="call_1"),
        ]
        result = comp.micro_compact(msgs)
        assert result == msgs

    def test_micro_compact_summarizes_long_tool_result(self):
        comp = ContextCompressor(micro_max_chars=40)
        long_result = "line one\n" + ("x" * 120)
        msgs = [Message(role="tool", content=long_result, name="Read", tool_call_id="call_1")]

        result = comp.micro_compact(msgs)

        assert len(result) == 1
        assert result[0].tool_call_id == "call_1"
        assert result[0].name == "Read"
        assert result[0].content.startswith("[tool result cached:")
        assert len(result[0].content) < len(long_result)

    def test_micro_compact_reuses_duplicate_tool_results(self):
        comp = ContextCompressor()
        msgs = [
            Message(role="tool", content="same result", name="Read", tool_call_id="call_1"),
            Message(role="tool", content="same result", name="Read", tool_call_id="call_2"),
        ]

        result = comp.micro_compact(msgs)

        assert result[0].content == "same result"
        assert result[1].content == "[cached Read result from call_1]"
        assert result[1].tool_call_id == "call_2"

    def test_context_collapse_short(self):
        comp = ContextCompressor()
        msgs = [Message(role="user", content=f"msg_{i}") for i in range(5)]
        result = comp.context_collapse(msgs, "goal")
        assert result == msgs  # Too short to collapse

    def test_context_collapse_long(self):
        comp = ContextCompressor()
        msgs = [Message(role="user", content=f"msg_{i}") for i in range(20)]
        result = comp.context_collapse(msgs, "goal")
        assert len(result) < 20
        assert len(result) == 9  # 3 + 1 (summary) + 5

    def test_auto_compact(self):
        comp = ContextCompressor()
        msgs = [Message(role="user", content=f"message about goal number {i}") for i in range(10)]
        result = comp.auto_compact(msgs, "goal")
        assert len(result) >= 5

    def test_auto_compact_few_messages(self):
        comp = ContextCompressor()
        msgs = [Message(role="user", content="test")]
        result = comp.auto_compact(msgs, "goal")
        assert len(result) == 1

    def test_relevance_matching(self):
        comp = ContextCompressor()
        score = comp._relevance("hello world goal test", "goal test")
        assert score > 0

    def test_relevance_no_match(self):
        comp = ContextCompressor()
        score = comp._relevance("hello world", "completely different")
        assert score == 0.0

    def test_relevance_empty_goal(self):
        comp = ContextCompressor()
        score = comp._relevance("anything", "")
        assert score == 0.5


# ── ContextRenewer ──

class TestContextRenewer:
    def test_creation(self):
        renewer = ContextRenewer()
        assert renewer.compressor is not None
        assert renewer.persistent is not None

    def test_renew(self):
        renewer = ContextRenewer()
        partitions = ContextPartitions()

        # Add some data
        partitions.working.rho = 1.0
        partitions.working.token_budget = 512
        partitions.working.plan = ["step1", "step2"]
        partitions.working.scratchpad = "notes"
        partitions.working.event_surface.pending_events = [{"event": "test"}]
        partitions.working.event_surface.recent_event_decisions = [
            {"event_id": f"e{i}", "action": "handled"} for i in range(7)
        ]
        partitions.working.knowledge_surface.active_questions = ["q1"]
        partitions.working.knowledge_surface.citations = ["doc-1"]
        partitions.history = [Message(role="user", content="test message")]

        result, handoff = renewer.renew(partitions, "my goal")
        assert result is not None
        # System and working should be preserved
        assert result.system == partitions.system
        assert result.working.rho == 1.0
        assert result.working.token_budget == 512
        assert result.working.plan == ["step1", "step2"]
        assert result.working.scratchpad == "notes"
        assert result.working.event_surface.pending_events == [{"event": "test"}]
        assert len(result.working.event_surface.recent_event_decisions) == 5
        assert result.working.knowledge_surface.active_questions == ["q1"]
        assert result.working.knowledge_surface.citations == ["doc-1"]
        # History should be compressed
        assert result.history is not None
        # HandoffArtifact
        assert handoff.goal == "my goal"
        assert handoff.sprint == 0
        assert handoff.open_tasks == ["step1", "step2"]

    def test_renew_creates_fresh_working_state(self):
        renewer = ContextRenewer()
        partitions = ContextPartitions()
        partitions.working.plan = ["step1"]
        partitions.working.event_surface.pending_events = [{"event_id": "e1"}]

        result, handoff = renewer.renew(partitions, "goal")

        assert result.working is not partitions.working
        result.working.plan.append("step2")
        assert partitions.working.plan == ["step1"]
        assert handoff.goal == "goal"


# ── EventAggregator ──

class TestEventAggregator:
    def test_creation(self):
        agg = EventAggregator()
        assert agg is not None

    def test_aggregate_empty(self):
        agg = EventAggregator()
        result = agg.aggregate([])
        assert result == []

    def test_aggregate_few_events(self):
        agg = EventAggregator()
        events = [
            {"source": "fs", "summary": "file changed", "delta_H": 0.3},
            {"source": "fs", "summary": "file changed", "delta_H": 0.3},
        ]
        result = agg.aggregate(events)
        assert len(result) <= len(events)

    def test_aggregate_many_similar_events(self):
        agg = EventAggregator()
        events = [
            {"source": "fs", "summary": "file changed", "delta_H": 0.3},
        ] * 10
        result = agg.aggregate(events)
        # Should be compressed
        assert len(result) < len(events)


# ── DashboardManager ──

class TestDashboardManager:
    def test_creation(self):
        dm = DashboardManager()
        assert dm is not None
        assert isinstance(dm.dashboard, Dashboard)

    def test_update_rho(self):
        dm = DashboardManager()
        dm.update_rho(0.75)
        assert dm.dashboard.rho == 0.75

    def test_update_progress(self):
        dm = DashboardManager()
        dm.update_progress("50% done")
        assert dm.dashboard.goal_progress == "50% done"

    def test_add_pending_event(self):
        dm = DashboardManager()
        dm.add_pending_event({"event_id": "e1", "type": "test"})
        assert len(dm.dashboard.event_surface.pending_events) == 1

    def test_add_pending_event_deduplicates(self):
        dm = DashboardManager()
        dm.add_pending_event({"event_id": "e1", "type": "test"})
        dm.add_pending_event({"event_id": "e1", "type": "test"})
        assert len(dm.dashboard.event_surface.pending_events) == 1

    def test_acknowledge_event(self):
        dm = DashboardManager()
        dm.add_pending_event({"event_id": "e1"})
        dm.add_active_risk({"event_id": "e1", "risk": "high"})
        dm.acknowledge_event("e1", {"action": "handled"})
        assert len(dm.dashboard.event_surface.pending_events) == 0
        assert len(dm.dashboard.event_surface.active_risks) == 0
        assert len(dm.dashboard.event_surface.recent_event_decisions) == 1

    def test_add_active_risk(self):
        dm = DashboardManager()
        dm.add_active_risk({"risk": "high"})
        assert len(dm.dashboard.event_surface.active_risks) == 1

    def test_add_question(self):
        dm = DashboardManager()
        dm.add_question("What to do?")
        assert "What to do?" in dm.dashboard.knowledge_surface.active_questions

    def test_add_question_deduplicates(self):
        dm = DashboardManager()
        dm.add_question("What to do?")
        dm.add_question("What to do?")
        assert dm.dashboard.knowledge_surface.active_questions == ["What to do?"]

    def test_add_evidence(self):
        dm = DashboardManager()
        dm.add_evidence({"fact": "data", "citation": "doc-1"})
        assert len(dm.dashboard.knowledge_surface.evidence_packs) == 1
        assert dm.dashboard.knowledge_surface.citations == ["doc-1"]

    def test_increment_errors(self):
        dm = DashboardManager()
        dm.increment_errors()
        dm.increment_errors()
        assert dm.dashboard.error_count == 2

    def test_update_heartbeat(self):
        dm = DashboardManager()
        dm.update_heartbeat("2024-01-01T00:00:00")
        assert dm.dashboard.last_hb_ts == "2024-01-01T00:00:00"

    def test_request_interrupt(self):
        dm = DashboardManager()
        dm.request_interrupt()
        assert dm.dashboard.interrupt_requested is True

    def test_bind_dashboard(self):
        dashboard = Dashboard(goal_progress="bound")
        dm = DashboardManager()

        dm.bind(dashboard)
        dm.update_rho(0.6)

        assert dm.dashboard is dashboard
        assert dashboard.rho == 0.6

    def test_decision_state(self):
        dm = DashboardManager()
        dm.update_progress("50% done")
        dm.add_pending_event({"event_id": "e1"})
        dm.add_active_risk({"event_id": "e1"})
        dm.add_question("What changed?")
        dm.increment_errors()
        dm.request_interrupt()

        state = dm.decision_state()

        assert state["interrupt_requested"] is True
        assert state["pending_events"] == 1
        assert state["active_risks"] == 1
        assert state["active_questions"] == 1
        assert state["error_count"] == 1
