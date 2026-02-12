"""
Tests for loom/memory/manager.py - MemoryManager, ContextEntry
"""

from unittest.mock import AsyncMock, MagicMock, patch

from loom.memory.manager import ContextEntry, MemoryManager


# ==================== ContextEntry ====================


class TestContextEntry:
    def test_init(self):
        entry = ContextEntry(id="ctx1", content="hello", created_by="agent-1")
        assert entry.id == "ctx1"
        assert entry.content == "hello"
        assert entry.created_by == "agent-1"

    def test_any_content(self):
        entry = ContextEntry(id="x", content={"key": [1, 2]}, created_by="a")
        assert entry.content == {"key": [1, 2]}


# ==================== MemoryManager ====================


class TestMemoryManagerInit:
    def test_defaults(self):
        mgr = MemoryManager(node_id="root")
        assert mgr.node_id == "root"
        assert mgr.parent is None
        assert mgr.children_count == 0
        assert mgr._context == {}

    def test_with_parent(self):
        parent = MemoryManager(node_id="parent")
        child = MemoryManager(node_id="child", parent=parent)
        assert child.parent is parent
        assert parent.children_count == 1


class TestMemoryManagerChildren:
    def test_register_child(self):
        parent = MemoryManager(node_id="p")
        child = MemoryManager(node_id="c")
        parent.register_child(child)
        assert parent.children_count == 1

    def test_register_child_idempotent(self):
        parent = MemoryManager(node_id="p")
        child = MemoryManager(node_id="c")
        parent.register_child(child)
        parent.register_child(child)
        assert parent.children_count == 1

    def test_unregister_child(self):
        parent = MemoryManager(node_id="p")
        child = MemoryManager(node_id="c", parent=parent)
        parent.unregister_child(child)
        assert parent.children_count == 0

    def test_unregister_missing_child(self):
        parent = MemoryManager(node_id="p")
        child = MemoryManager(node_id="c")
        parent.unregister_child(child)  # should not raise


class TestMemoryManagerContext:
    async def test_add_context(self):
        mgr = MemoryManager(node_id="root")
        entry = await mgr.add_context("ctx1", "data")
        assert entry.id == "ctx1"
        assert entry.content == "data"
        assert entry.created_by == "root"

    async def test_read_local(self):
        mgr = MemoryManager(node_id="root")
        await mgr.add_context("ctx1", "data")
        entry = await mgr.read("ctx1")
        assert entry is not None
        assert entry.content == "data"

    async def test_read_missing(self):
        mgr = MemoryManager(node_id="root")
        entry = await mgr.read("nonexistent")
        assert entry is None

    async def test_read_from_parent(self):
        parent = MemoryManager(node_id="parent")
        child = MemoryManager(node_id="child", parent=parent)
        await parent.add_context("shared", "parent_data")
        entry = await child.read("shared")
        assert entry is not None
        assert entry.content == "parent_data"

    async def test_list_context(self):
        mgr = MemoryManager(node_id="root")
        await mgr.add_context("a", 1)
        await mgr.add_context("b", 2)
        entries = await mgr.list_context()
        assert len(entries) == 2


class TestMemoryManagerLoomMemoryProxy:
    def test_add_task(self):
        mgr = MemoryManager(node_id="root")
        task = MagicMock()
        mgr._loom_memory.add_task = MagicMock()
        mgr.add_task(task)
        mgr._loom_memory.add_task.assert_called_once_with(task)

    def test_get_l1_tasks(self):
        mgr = MemoryManager(node_id="root")
        mgr._loom_memory.get_l1_tasks = MagicMock(return_value=[])
        result = mgr.get_l1_tasks(limit=5)
        assert result == []

    def test_get_l2_tasks(self):
        mgr = MemoryManager(node_id="root")
        mgr._loom_memory.get_l2_tasks = MagicMock(return_value=[])
        result = mgr.get_l2_tasks()
        assert result == []

    def test_get_task(self):
        mgr = MemoryManager(node_id="root")
        mgr._loom_memory.get_task = MagicMock(return_value=None)
        assert mgr.get_task("t1") is None

    def test_promote_tasks(self):
        mgr = MemoryManager(node_id="root")
        mgr._loom_memory.promote_tasks = MagicMock()
        mgr.promote_tasks()
        mgr._loom_memory.promote_tasks.assert_called_once()

    def test_promote_task_to_l2(self):
        mgr = MemoryManager(node_id="root")
        task = MagicMock()
        mgr._loom_memory.promote_task_to_l2 = MagicMock(return_value=True)
        assert mgr.promote_task_to_l2(task) is True

    async def test_promote_tasks_async(self):
        mgr = MemoryManager(node_id="root")
        mgr._loom_memory.promote_tasks_async = AsyncMock()
        await mgr.promote_tasks_async()
        mgr._loom_memory.promote_tasks_async.assert_called_once()

    def test_set_vector_store(self):
        mgr = MemoryManager(node_id="root")
        store = MagicMock()
        mgr._loom_memory.set_vector_store = MagicMock()
        mgr.set_vector_store(store)
        mgr._loom_memory.set_vector_store.assert_called_once_with(store)

    def test_set_embedding_provider(self):
        mgr = MemoryManager(node_id="root")
        provider = MagicMock()
        mgr._loom_memory.set_embedding_provider = MagicMock()
        mgr.set_embedding_provider(provider)
        mgr._loom_memory.set_embedding_provider.assert_called_once_with(provider)


class TestMemoryManagerStats:
    def test_get_context_stats(self):
        mgr = MemoryManager(node_id="root")
        stats = mgr.get_context_stats()
        assert stats == {"context_count": 0}

    def test_get_manager_state(self):
        mgr = MemoryManager(node_id="root")
        state = mgr.get_manager_state()
        assert state["node_id"] == "root"
        assert state["children_count"] == 0
        assert state["has_parent"] is False
        assert "loom_memory_stats" in state


class TestMemoryManagerSnapshot:
    def test_export_snapshot(self):
        mgr = MemoryManager(node_id="root")
        snapshot = mgr.export_snapshot()
        assert snapshot["node_id"] == "root"
        assert "l1_items" in snapshot
        assert "l2_items" in snapshot
        assert "context" in snapshot

    async def test_export_with_context(self):
        mgr = MemoryManager(node_id="root")
        await mgr.add_context("k1", "v1")
        snapshot = mgr.export_snapshot()
        assert "k1" in snapshot["context"]
        assert snapshot["context"]["k1"]["content"] == "v1"

    def test_restore_empty_snapshot(self):
        mgr = MemoryManager(node_id="root")
        mgr.restore_snapshot({})  # should not raise

    def test_restore_none_snapshot(self):
        mgr = MemoryManager(node_id="root")
        mgr.restore_snapshot(None)  # should not raise

    async def test_restore_context(self):
        mgr = MemoryManager(node_id="root")
        snapshot = {
            "l1_items": [],
            "l2_items": [],
            "context": {
                "k1": {"id": "k1", "content": "restored", "created_by": "old"},
            },
        }
        mgr.restore_snapshot(snapshot)
        entry = await mgr.read("k1")
        assert entry is not None
        assert entry.content == "restored"
