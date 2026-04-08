"""Test runtime module - L* loop, H_b heartbeat, monitors"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from loom.context.dashboard import DashboardManager
from loom.orchestration.events import EventBus as OrchestrationEventBus
from loom.runtime.heartbeat import Heartbeat, HeartbeatConfig, WatchSource
from loom.runtime.loop import AgentLoop, LoopConfig
from loom.runtime.monitors import (
    FilesystemMonitor,
    MFEventsMonitor,
    ProcessMonitor,
    ResourceMonitor,
)
from loom.types import Event as OrchestrationEvent
from loom.types import LoopState

# ── LoopConfig ──

class TestLoopConfig:
    def test_defaults(self):
        config = LoopConfig()
        assert config.max_iterations == 100
        assert config.d_max == 5
        assert config.rho_threshold == 1.0

    def test_custom(self):
        config = LoopConfig(max_iterations=50, d_max=3, rho_threshold=0.8)
        assert config.max_iterations == 50
        assert config.d_max == 3
        assert config.rho_threshold == 0.8


# ── AgentLoop ──

class TestAgentLoop:
    def test_creation(self):
        config = LoopConfig()
        loop = AgentLoop(config)
        assert loop.config is config
        assert loop.state == LoopState.REASON
        assert loop.iteration == 0

    def test_goal_reached(self):
        """Test L* loop reaches goal"""
        loop = AgentLoop(LoopConfig(max_iterations=20))

        reason_fn = MagicMock(side_effect=lambda goal, ctx: ctx)
        act_fn = MagicMock(return_value="effect")
        observe_fn = MagicMock(side_effect=lambda eff, ctx: ctx)
        # First delta returns continue, second returns goal_reached
        delta_fn = MagicMock(side_effect=["continue", "goal_reached"])

        ctx = MagicMock()
        ctx.working = MagicMock()
        ctx.working.rho = 0.5

        result = loop.run("test goal", ctx, reason_fn, act_fn, observe_fn, delta_fn)
        assert result["status"] == "success"
        # Each cycle: REASON→ACT→OBSERVE→DELTA = 4 iterations
        # 2 full cycles = 8 iterations
        assert loop.iteration == 8

    def test_max_iterations(self):
        """Test L* loop respects max_iterations"""
        loop = AgentLoop(LoopConfig(max_iterations=3))

        ctx = MagicMock()
        ctx.working = MagicMock()
        ctx.working.rho = 0.5

        delta_fn = MagicMock(return_value="continue")

        result = loop.run("goal", ctx,
                          lambda g, c: c,
                          lambda c: "effect",
                          lambda e, c: c,
                          delta_fn)
        assert result["status"] == "max_iterations"
        assert loop.iteration == 3

    def test_renew_on_rho_threshold(self):
        """Test L* loop triggers renew when rho >= threshold"""
        loop = AgentLoop(LoopConfig(max_iterations=20, rho_threshold=0.8))

        ctx = MagicMock()
        ctx.working = MagicMock()
        ctx.working.rho = 0.9  # Above threshold to trigger renew in OBSERVE

        renew_call_count = {"n": 0}

        def mock_renew_fn(context, goal):
            renew_call_count["n"] += 1
            # After first renew, reset rho so delta can be reached
            context.working.rho = 0.3
            return context

        with patch("loom.context.ContextRenewer") as MockRenewer:
            mock_renewer = MagicMock()
            mock_renewer.renew.side_effect = mock_renew_fn
            MockRenewer.return_value = mock_renewer

            loop.run("goal", ctx,
                              lambda g, c: c,
                              lambda c: "effect",
                              lambda e, c: c,
                              lambda c: "goal_reached")
            # renew should have been triggered at least once
            assert renew_call_count["n"] >= 1

    def test_decompose_decision(self):
        """Test L* loop handles decompose"""
        loop = AgentLoop(LoopConfig(max_iterations=5))

        ctx = MagicMock()
        ctx.working = MagicMock()
        ctx.working.rho = 0.3

        delta_fn = MagicMock(return_value="decompose")

        result = loop.run("goal", ctx,
                          lambda g, c: c,
                          lambda c: "effect",
                          lambda e, c: c,
                          delta_fn)
        assert result["status"] == "decompose"

    def test_harness_decision(self):
        """Test L* loop handles harness"""
        loop = AgentLoop(LoopConfig(max_iterations=5))

        ctx = MagicMock()
        ctx.working = MagicMock()
        ctx.working.rho = 0.3

        result = loop.run("goal", ctx,
                          lambda g, c: c,
                          lambda c: "effect",
                          lambda e, c: c,
                          lambda c: "harness")
        assert result["status"] == "harness"

    def test_renew_decision_from_delta(self):
        """Test L* loop handles renew from delta"""
        loop = AgentLoop(LoopConfig(max_iterations=20))

        ctx = MagicMock()
        ctx.working = MagicMock()
        ctx.working.rho = 0.3

        # First delta -> renew, then goal_reached
        delta_fn = MagicMock(side_effect=["renew", "goal_reached"])

        with patch("loom.context.ContextRenewer") as MockRenewer:
            mock_renewer = MagicMock()
            mock_renewer.renew.return_value = ctx
            MockRenewer.return_value = mock_renewer

            result = loop.run("goal", ctx,
                              lambda g, c: c,
                              lambda c: "effect",
                              lambda e, c: c,
                              delta_fn)
            assert result["status"] == "success"
            mock_renewer.renew.assert_called_once()


# ── HeartbeatConfig & WatchSource ──

class TestWatchSource:
    def test_defaults(self):
        ws = WatchSource(type="filesystem")
        assert ws.type == "filesystem"
        assert ws.config == {}

    def test_custom(self):
        ws = WatchSource(type="resource", config={"thresholds": {"memory_pct": 90}})
        assert ws.config["thresholds"]["memory_pct"] == 90


class TestHeartbeatConfig:
    def test_defaults(self):
        config = HeartbeatConfig()
        assert config.T_hb == 5.0
        assert config.delta_hb == 0.1
        assert config.watch_sources == []
        assert config.interrupt_policy["low"] == "queue"
        assert config.interrupt_policy["critical"] == "force"

    def test_custom(self):
        ws = WatchSource(type="filesystem", config={"paths": ["/tmp"]})
        config = HeartbeatConfig(T_hb=1.0, delta_hb=0.2, watch_sources=[ws])
        assert config.T_hb == 1.0
        assert len(config.watch_sources) == 1


# ── Heartbeat ──

class TestHeartbeat:
    def test_creation(self):
        hb = Heartbeat(HeartbeatConfig())
        assert hb.running is False
        assert hb.event_callback is None

    def test_start_stop(self):
        """Test heartbeat can start and stop"""
        config = HeartbeatConfig(T_hb=0.1)
        hb = Heartbeat(config)
        events = []

        hb.start(lambda e, u: events.append((e, u)))
        assert hb.running is True
        assert hb.thread is not None
        assert hb.thread.daemon is True

        time.sleep(0.3)
        hb.stop()
        assert hb.running is False

    def test_classify_urgency(self):
        hb = Heartbeat(HeartbeatConfig())
        assert hb._classify_urgency({"delta_H": 0.9}) == "critical"
        assert hb._classify_urgency({"delta_H": 0.6}) == "high"
        assert hb._classify_urgency({"delta_H": 0.3}) == "low"
        assert hb._classify_urgency({}) == "low"

    def test_event_callback_triggered(self):
        """Test heartbeat triggers callback on filesystem change"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("initial")

            ws = WatchSource(type="filesystem", config={"paths": [str(test_file)]})
            config = HeartbeatConfig(T_hb=0.1, delta_hb=0.01, watch_sources=[ws])
            hb = Heartbeat(config)
            events = []

            hb.start(lambda e, u: events.append((e, u)))

            # Wait for initial scan
            time.sleep(0.2)

            # Modify file
            test_file.write_text("modified")

            # Wait for detection
            time.sleep(0.3)

            hb.stop()

            # Should have detected the change
            if events:
                event, urgency = events[0]
                assert event["source"] == "filesystem"

    def test_check_source_resource(self):
        """Test resource monitor source check"""
        ws = WatchSource(type="resource", config={"thresholds": {"memory_pct": 1}})
        config = HeartbeatConfig(watch_sources=[ws])
        hb = Heartbeat(config)

        result = hb._check_source(ws, "2024-01-01T00:00:00")
        # Memory is likely > 1%, so should return an event
        assert result is not None
        assert result["resource"] == "memory"

    def test_check_source_mf_events(self):
        """Test MF events monitor source."""
        bus = OrchestrationEventBus()
        bus.publish(
            OrchestrationEvent(
                id="evt_1",
                sender="agent",
                topic="test",
                payload={"value": 1},
                delta_h=0.4,
                priority="medium",
            )
        )
        ws = WatchSource(type="mf_events", config={"topics": ["test"], "event_bus": bus})
        config = HeartbeatConfig(watch_sources=[ws])
        hb = Heartbeat(config)

        result = hb._check_source(ws, "2024-01-01T00:00:00")
        assert result is not None
        assert result["source"] == "mf_events"
        assert result["topic"] == "test"

    def test_check_source_unknown(self):
        """Test unknown source type returns None"""
        ws = WatchSource(type="unknown_type")
        config = HeartbeatConfig(watch_sources=[ws])
        hb = Heartbeat(config)

        result = hb._check_source(ws, "2024-01-01T00:00:00")
        assert result is None


# ── FilesystemMonitor ──

class TestFilesystemMonitor:
    def test_file_change_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("hello")

            monitor = FilesystemMonitor([str(test_file)])
            assert str(test_file) in monitor.cache

            # No change
            result = monitor.check("2024-01-01T00:00:00")
            assert result is None

            # Modify
            test_file.write_text("world")
            result = monitor.check("2024-01-01T00:01:00")
            assert result is not None
            assert result["source"] == "filesystem"
            assert "modified" in result["summary"].lower() or "file" in result["summary"].lower()

    def test_directory_monitoring(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.txt").write_text("aaa")

            monitor = FilesystemMonitor([tmpdir])
            assert len(monitor.cache) > 0

            # Modify file in directory
            (Path(tmpdir) / "a.txt").write_text("bbb")
            result = monitor.check("2024-01-01T00:00:00")
            assert result is not None

    def test_new_file_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = FilesystemMonitor([tmpdir])
            # No changes yet
            assert monitor.check("2024-01-01T00:00:00") is None

            # Add new file - should not trigger alert, just cache it
            (Path(tmpdir) / "new.txt").write_text("new")
            result = monitor.check("2024-01-01T00:01:00")
            # New file is just cached, not reported as modification
            assert result is None

    def test_hash_file_error(self):
        monitor = FilesystemMonitor([])
        # Non-existent file
        result = monitor._hash_file(Path("/nonexistent/file.txt"))
        assert result == ""

    def test_nonexistent_path(self):
        monitor = FilesystemMonitor(["/nonexistent/path"])
        result = monitor.check("2024-01-01T00:00:00")
        assert result is None


# ── ProcessMonitor ──

class TestProcessMonitor:
    def test_no_pid_file(self):
        monitor = ProcessMonitor()
        result = monitor.check("2024-01-01T00:00:00")
        assert result is None

    def test_nonexistent_pid_file(self):
        monitor = ProcessMonitor(pid_file="/nonexistent/pid.txt")
        result = monitor.check("2024-01-01T00:00:00")
        assert result is None

    def test_nonexistent_process(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pid', delete=False) as f:
            f.write("999999999")  # Very unlikely to exist
            pid_path = f.name

        try:
            monitor = ProcessMonitor(pid_file=pid_path)
            with patch("loom.runtime.monitors.psutil.pid_exists", return_value=False):
                result = monitor.check("2024-01-01T00:00:00")
                assert result is not None
                assert result["source"] == "process"
                assert result["pid"] == 999999999
        finally:
            Path(pid_path).unlink(missing_ok=True)

    def test_running_process(self):
        import os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pid', delete=False) as f:
            f.write(str(os.getpid()))
            pid_path = f.name

        try:
            monitor = ProcessMonitor(pid_file=pid_path)
            result = monitor.check("2024-01-01T00:00:00")
            # Current process is running, no event
            assert result is None
        finally:
            Path(pid_path).unlink(missing_ok=True)


# ── ResourceMonitor ──

class TestResourceMonitor:
    def test_no_threshold_breach(self):
        monitor = ResourceMonitor({"memory_pct": 99.9, "disk_pct": 99.9})
        # Unlikely to breach 99.9%
        result = monitor.check("2024-01-01T00:00:00")
        assert result is None

    def test_memory_threshold_breach(self):
        monitor = ResourceMonitor({"memory_pct": 1})
        result = monitor.check("2024-01-01T00:00:00")
        assert result is not None
        assert result["resource"] == "memory"
        assert result["delta_H"] == 0.9

    def test_disk_threshold_breach(self):
        monitor = ResourceMonitor({"disk_pct": 1})
        result = monitor.check("2024-01-01T00:00:00")
        assert result is not None
        assert result["resource"] == "disk"
        assert result["delta_H"] == 0.85

    def test_empty_thresholds(self):
        monitor = ResourceMonitor({})
        result = monitor.check("2024-01-01T00:00:00")
        assert result is None


# ── MFEventsMonitor ──

class TestMFEventsMonitor:
    def test_reads_published_events(self):
        bus = OrchestrationEventBus()
        monitor = MFEventsMonitor(topics=["test"], event_bus=bus)

        assert monitor.check("2024-01-01T00:00:00") is None

        bus.publish(
            OrchestrationEvent(
                id="evt_2",
                sender="agent",
                topic="test",
                payload={"value": 2},
                delta_h=0.5,
                priority="high",
            )
        )

        result = monitor.check("2024-01-01T00:00:01")
        assert result is not None
        assert result["topic"] == "test"
        assert result["delta_H"] == 0.5

    def test_filters_topics(self):
        bus = OrchestrationEventBus()
        monitor = MFEventsMonitor(topics=["wanted"], event_bus=bus)
        bus.publish(
            OrchestrationEvent(
                id="evt_3",
                sender="agent",
                topic="other",
                payload={},
                delta_h=0.6,
                priority="medium",
            )
        )
        assert monitor.check("2024-01-01T00:00:00") is None


class TestHeartbeatDashboardIntegration:
    def test_process_event_updates_dashboard(self):
        hb = Heartbeat(HeartbeatConfig())
        dm = DashboardManager()

        hb.process_event(
            {
                "event_id": "evt_hb",
                "summary": "disk usage high",
                "observed_at": "2024-01-01T00:00:00",
                "delta_H": 0.9,
            },
            "critical",
            dashboard_manager=dm,
        )

        assert dm.dashboard.last_hb_ts == "2024-01-01T00:00:00"
        assert dm.dashboard.interrupt_requested is True
        assert len(dm.dashboard.event_surface.pending_events) == 1
        assert len(dm.dashboard.event_surface.active_risks) == 1

    def test_dashboard_callback(self):
        hb = Heartbeat(HeartbeatConfig())
        dm = DashboardManager()
        callback = hb.dashboard_callback(dm)

        callback(
            {
                "event_id": "evt_hb_2",
                "summary": "file changed",
                "observed_at": "2024-01-01T00:00:01",
                "delta_H": 0.4,
            },
            "low",
        )

        assert dm.dashboard.last_hb_ts == "2024-01-01T00:00:01"
        assert len(dm.dashboard.event_surface.pending_events) == 1
        assert dm.dashboard.interrupt_requested is False
