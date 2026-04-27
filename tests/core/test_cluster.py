"""Test cluster module - fork, event_bus, shared_memory"""

import tempfile
from pathlib import Path

import pytest

from loom.experimental.cluster.event_bus import Event, EventBus
from loom.experimental.cluster.fork import AgentFork, SubAgentConfig
from loom.experimental.cluster.shared_memory import SharedMemory

# ── SubAgentConfig ──


class TestSubAgentConfig:
    def test_defaults(self):
        config = SubAgentConfig(goal="test", depth=1, parent_id="p1")
        assert config.goal == "test"
        assert config.depth == 1
        assert config.parent_id == "p1"
        assert config.max_depth == 5

    def test_custom_max_depth(self):
        config = SubAgentConfig(goal="test", depth=1, parent_id="p1", max_depth=10)
        assert config.max_depth == 10


# ── AgentFork ──


class TestAgentFork:
    def test_creation(self):
        fork = AgentFork()
        assert fork.max_depth == 5
        assert fork.active_agents == {}

    def test_custom_max_depth(self):
        fork = AgentFork(max_depth=10)
        assert fork.max_depth == 10

    def test_can_fork(self):
        fork = AgentFork(max_depth=5)
        assert fork.can_fork(0) is True
        assert fork.can_fork(4) is True
        assert fork.can_fork(5) is False

    def test_spawn(self):
        fork = AgentFork(max_depth=5)
        config = SubAgentConfig(goal="sub task", depth=0, parent_id="parent")
        agent_id = fork.spawn(config)
        assert agent_id == "agent_parent_0"
        assert agent_id in fork.active_agents
        assert fork.active_agents[agent_id]["status"] == "running"
        assert fork.active_agents[agent_id]["config"] is config

    def test_spawn_multiple(self):
        fork = AgentFork(max_depth=5)
        config1 = SubAgentConfig(goal="task1", depth=0, parent_id="p")
        config2 = SubAgentConfig(goal="task2", depth=1, parent_id="p")
        id1 = fork.spawn(config1)
        id2 = fork.spawn(config2)
        assert id1 != id2
        assert len(fork.active_agents) == 2

    def test_spawn_exceeds_depth(self):
        fork = AgentFork(max_depth=3)
        config = SubAgentConfig(goal="task", depth=3, parent_id="p")
        with pytest.raises(ValueError, match="Max depth"):
            fork.spawn(config)

    def test_get_result(self):
        fork = AgentFork()
        config = SubAgentConfig(goal="task", depth=0, parent_id="p")
        agent_id = fork.spawn(config)
        result = fork.get_result(agent_id)
        assert result is not None
        assert result["status"] == "running"

    def test_get_result_not_found(self):
        fork = AgentFork()
        result = fork.get_result("nonexistent")
        assert result is None


# ── Event (cluster) ──


class TestClusterEvent:
    def test_event_creation(self):
        event = Event(
            event_id="evt_001",
            source="test",
            data={"key": "value"},
            delta_H=0.5,
            timestamp="2024-01-01T00:00:00",
        )
        assert event.event_id == "evt_001"
        assert event.source == "test"
        assert event.data == {"key": "value"}
        assert event.delta_H == 0.5


# ── EventBus (cluster) ──


class TestClusterEventBus:
    def test_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bus = EventBus(Path(tmpdir) / "events")
            assert bus.subscribers == {}

    def test_publish_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bus = EventBus(Path(tmpdir) / "events")
            event = Event(
                event_id="evt_001",
                source="agent_1",
                data={"action": "complete"},
                delta_H=0.7,
                timestamp="2024-01-01T00:00:00",
            )
            bus.publish(event)

            # Verify file written
            events = bus.read_events()
            assert len(events) == 1
            assert events[0].event_id == "evt_001"
            assert events[0].source == "agent_1"
            assert events[0].delta_H == 0.7

    def test_publish_with_subscriber(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bus = EventBus(Path(tmpdir) / "events")
            received = []

            bus.subscribe("agent_1", lambda e: received.append(e))

            event = Event(
                event_id="evt_002",
                source="agent_1",
                data={},
                delta_H=0.3,
                timestamp="2024-01-01T00:00:00",
            )
            bus.publish(event)
            assert len(received) == 1
            assert received[0].event_id == "evt_002"

    def test_subscribe_no_callback_for_other_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bus = EventBus(Path(tmpdir) / "events")
            received = []

            bus.subscribe("agent_1", lambda e: received.append(e))

            event = Event(
                event_id="evt_003",
                source="agent_2",
                data={},
                delta_H=0.3,
                timestamp="2024-01-01T00:00:00",
            )
            bus.publish(event)
            assert len(received) == 0

    def test_read_events_since(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bus = EventBus(Path(tmpdir) / "events")

            for i in range(3):
                event = Event(
                    event_id=f"evt_{i}",
                    source="src",
                    data={"i": i},
                    delta_H=0.5,
                    timestamp="2024-01-01T00:00:00",
                )
                bus.publish(event)

            events = bus.read_events()
            assert len(events) == 3

    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = Path(tmpdir) / "new" / "sub" / "dir"
            EventBus(new_path)
            assert new_path.exists()


# ── SharedMemory ──


class TestSharedMemory:
    def test_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SharedMemory(Path(tmpdir) / "shared")
            assert sm.base_path.exists()

    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SharedMemory(Path(tmpdir) / "shared")
            sm.write("key1", {"name": "test", "value": 42})

            result = sm.read("key1")
            assert result == {"name": "test", "value": 42}

    def test_read_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SharedMemory(Path(tmpdir) / "shared")
            result = sm.read("nonexistent")
            assert result is None

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SharedMemory(Path(tmpdir) / "shared")
            sm.write("key1", {"data": "test"})
            assert sm.read("key1") is not None

            sm.delete("key1")
            assert sm.read("key1") is None

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SharedMemory(Path(tmpdir) / "shared")
            # Should not raise
            sm.delete("nonexistent")

    def test_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SharedMemory(Path(tmpdir) / "shared")
            sm.write("key1", {"v": 1})
            sm.write("key1", {"v": 2})
            assert sm.read("key1") == {"v": 2}

    def test_multiple_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SharedMemory(Path(tmpdir) / "shared")
            sm.write("a", {"val": "a"})
            sm.write("b", {"val": "b"})
            sm.write("c", {"val": "c"})

            assert sm.read("a") == {"val": "a"}
            assert sm.read("b") == {"val": "b"}
            assert sm.read("c") == {"val": "c"}
