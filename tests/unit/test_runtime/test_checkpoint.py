"""
Tests for runtime/checkpoint.py
"""

import pytest

from loom.runtime.checkpoint import CheckpointData, CheckpointManager, CheckpointStatus
from loom.runtime.state_store import MemoryStateStore


# ============ CheckpointStatus ============


class TestCheckpointStatus:
    def test_enum_values(self):
        assert CheckpointStatus.CREATED.value == "created"
        assert CheckpointStatus.VALID.value == "valid"
        assert CheckpointStatus.CORRUPTED.value == "corrupted"
        assert CheckpointStatus.EXPIRED.value == "expired"


# ============ CheckpointData ============


class TestCheckpointData:
    def test_basic_creation(self):
        cp = CheckpointData(
            agent_id="a1", task_id="t1", iteration=5, max_iterations=30
        )
        assert cp.agent_id == "a1"
        assert cp.task_id == "t1"
        assert cp.iteration == 5
        assert cp.max_iterations == 30
        assert cp.status == CheckpointStatus.CREATED.value
        assert cp.timestamp > 0

    def test_to_dict(self):
        cp = CheckpointData(
            agent_id="a1", task_id="t1", iteration=3, max_iterations=10
        )
        d = cp.to_dict()
        assert d["agent_id"] == "a1"
        assert d["task_id"] == "t1"
        assert d["iteration"] == 3
        assert d["agent_state"] == {}
        assert d["memory_snapshot"] == {}
        assert d["tool_history"] == []

    def test_from_dict(self):
        data = {
            "agent_id": "a1",
            "task_id": "t1",
            "iteration": 7,
            "max_iterations": 20,
            "timestamp": 1000.0,
            "status": "valid",
            "agent_state": {"key": "val"},
            "memory_snapshot": {},
            "tool_history": [{"tool": "search"}],
            "context_metadata": {},
        }
        cp = CheckpointData.from_dict(data)
        assert cp.agent_id == "a1"
        assert cp.iteration == 7
        assert cp.status == "valid"
        assert cp.agent_state == {"key": "val"}

    def test_from_dict_default_status(self):
        data = {
            "agent_id": "a1",
            "task_id": "t1",
            "iteration": 0,
            "max_iterations": 10,
        }
        cp = CheckpointData.from_dict(data)
        assert cp.status == CheckpointStatus.CREATED.value

    def test_roundtrip(self):
        cp = CheckpointData(
            agent_id="a1",
            task_id="t1",
            iteration=5,
            max_iterations=30,
            agent_state={"step": 5},
            tool_history=[{"tool": "bash", "result": "ok"}],
        )
        d = cp.to_dict()
        cp2 = CheckpointData.from_dict(d)
        assert cp2.agent_id == cp.agent_id
        assert cp2.iteration == cp.iteration
        assert cp2.agent_state == cp.agent_state
        assert cp2.tool_history == cp.tool_history


# ============ CheckpointManager ============


class TestCheckpointManager:
    @pytest.fixture
    def store(self):
        return MemoryStateStore()

    @pytest.fixture
    def mgr(self, store):
        return CheckpointManager(store, max_checkpoints=5)

    async def test_save_and_load_latest(self, mgr):
        cp = CheckpointData(agent_id="a1", task_id="t1", iteration=1, max_iterations=10)
        await mgr.save(cp)
        loaded = await mgr.load_latest("a1", "t1")
        assert loaded is not None
        assert loaded.iteration == 1
        assert loaded.status == CheckpointStatus.VALID.value

    async def test_load_latest_returns_most_recent(self, mgr):
        for i in range(3):
            cp = CheckpointData(agent_id="a1", task_id="t1", iteration=i, max_iterations=10)
            await mgr.save(cp)
        loaded = await mgr.load_latest("a1", "t1")
        assert loaded.iteration == 2

    async def test_load_latest_no_checkpoints(self, mgr):
        loaded = await mgr.load_latest("a1", "t1")
        assert loaded is None

    async def test_load_specific_iteration(self, mgr):
        for i in range(3):
            cp = CheckpointData(agent_id="a1", task_id="t1", iteration=i, max_iterations=10)
            await mgr.save(cp)
        loaded = await mgr.load("a1", "t1", 1)
        assert loaded is not None
        assert loaded.iteration == 1

    async def test_load_nonexistent_iteration(self, mgr):
        loaded = await mgr.load("a1", "t1", 99)
        assert loaded is None

    async def test_cleanup_keeps_last_n(self, mgr):
        for i in range(8):
            cp = CheckpointData(agent_id="a1", task_id="t1", iteration=i, max_iterations=10)
            await mgr.save(cp)
        # max_checkpoints=5, so cleanup should have run
        iters = await mgr.list_checkpoints("a1", "t1")
        assert len(iters) <= 5

    async def test_cleanup_returns_deleted_count(self, store):
        mgr = CheckpointManager(store, max_checkpoints=100)
        for i in range(5):
            cp = CheckpointData(agent_id="a1", task_id="t1", iteration=i, max_iterations=10)
            await mgr.save(cp)
        deleted = await mgr.cleanup("a1", "t1", keep_last=2)
        assert deleted == 3

    async def test_cleanup_no_op_when_under_limit(self, mgr):
        cp = CheckpointData(agent_id="a1", task_id="t1", iteration=0, max_iterations=10)
        await mgr.save(cp)
        deleted = await mgr.cleanup("a1", "t1", keep_last=5)
        assert deleted == 0

    async def test_delete_all(self, mgr):
        for i in range(3):
            cp = CheckpointData(agent_id="a1", task_id="t1", iteration=i, max_iterations=10)
            await mgr.save(cp)
        count = await mgr.delete_all("a1", "t1")
        assert count >= 3
        loaded = await mgr.load_latest("a1", "t1")
        assert loaded is None

    async def test_list_checkpoints(self, mgr):
        for i in [0, 3, 7]:
            cp = CheckpointData(agent_id="a1", task_id="t1", iteration=i, max_iterations=10)
            await mgr.save(cp)
        iters = await mgr.list_checkpoints("a1", "t1")
        assert iters == [0, 3, 7]

    async def test_list_checkpoints_empty(self, mgr):
        iters = await mgr.list_checkpoints("a1", "t1")
        assert iters == []

    async def test_validate_rejects_corrupted(self, store):
        mgr = CheckpointManager(store, auto_validate=True)
        cp = CheckpointData(agent_id="a1", task_id="t1", iteration=1, max_iterations=10)
        cp.status = CheckpointStatus.CORRUPTED.value
        key = mgr._key("a1", "t1", 1)
        await store.save(key, cp.to_dict())
        loaded = await mgr.load_latest("a1", "t1")
        assert loaded is None

    async def test_validate_rejects_empty_agent_id(self, store):
        mgr = CheckpointManager(store, auto_validate=True)
        cp = CheckpointData(agent_id="", task_id="t1", iteration=1, max_iterations=10)
        cp.status = CheckpointStatus.VALID.value
        key = mgr._key("", "t1", 1)
        await store.save(key, cp.to_dict())
        loaded = await mgr.load_latest("", "t1")
        assert loaded is None

    async def test_negative_iteration_key_format(self, store):
        mgr = CheckpointManager(store, auto_validate=True)
        cp = CheckpointData(agent_id="a1", task_id="t1", iteration=-1, max_iterations=10)
        cp.status = CheckpointStatus.VALID.value
        key = mgr._key("a1", "t1", -1)
        await store.save(key, cp.to_dict())
        # Negative iteration produces unusual key but load still works
        loaded = await mgr.load("a1", "t1", -1)
        assert loaded is not None
        assert loaded.iteration == -1

    async def test_auto_validate_disabled(self, store):
        mgr = CheckpointManager(store, auto_validate=False)
        cp = CheckpointData(agent_id="a1", task_id="t1", iteration=1, max_iterations=10)
        cp.status = CheckpointStatus.CORRUPTED.value
        key = mgr._key("a1", "t1", 1)
        await store.save(key, cp.to_dict())
        loaded = await mgr.load_latest("a1", "t1")
        # With auto_validate=False, corrupted checkpoints are still returned
        assert loaded is not None

    async def test_key_format(self, mgr):
        key = mgr._key("agent-1", "task-1", 42)
        assert key == "checkpoint:agent-1:task-1:000042"

    async def test_prefix_with_task(self, mgr):
        prefix = mgr._prefix("agent-1", "task-1")
        assert prefix == "checkpoint:agent-1:task-1:"

    async def test_prefix_without_task(self, mgr):
        prefix = mgr._prefix("agent-1")
        assert prefix == "checkpoint:agent-1:"

    async def test_corrupted_data_skipped_on_load(self, store):
        mgr = CheckpointManager(store)
        key = mgr._key("a1", "t1", 1)
        await store.save(key, 42)  # non-dict triggers TypeError in dict()
        loaded = await mgr.load("a1", "t1", 1)
        assert loaded is None

    async def test_different_tasks_isolated(self, mgr):
        cp1 = CheckpointData(agent_id="a1", task_id="t1", iteration=1, max_iterations=10)
        cp2 = CheckpointData(agent_id="a1", task_id="t2", iteration=2, max_iterations=10)
        await mgr.save(cp1)
        await mgr.save(cp2)
        loaded1 = await mgr.load_latest("a1", "t1")
        loaded2 = await mgr.load_latest("a1", "t2")
        assert loaded1.iteration == 1
        assert loaded2.iteration == 2
