"""
Tests for loom/memory/manager.py - MemoryManager, ContextEntry
"""

from unittest.mock import MagicMock

from loom.memory.core import LoomMemory
from loom.memory.manager import ContextEntry, MemoryManager
from loom.memory.types import MemoryRecord, MemoryType, MessageItem, WorkingMemoryEntry

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

    def test_inject_memory(self):
        """测试注入 LoomMemory"""
        memory = LoomMemory(node_id="test", l1_token_budget=4000)
        mgr = MemoryManager(node_id="test", memory=memory)
        assert mgr.memory is memory

    def test_auto_create_memory(self):
        """测试自动创建 LoomMemory"""
        mgr = MemoryManager(node_id="test", l1_token_budget=4000, l2_token_budget=8000)
        assert mgr.memory is not None
        assert mgr.memory.l1.token_budget == 4000
        assert mgr.memory.l2.token_budget == 8000


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


class TestMemoryManagerL1Proxy:
    """测试 L1 消息级 API 代理"""

    def test_add_message(self):
        mgr = MemoryManager(node_id="root")
        evicted = mgr.add_message("user", "Hello", token_count=5)
        assert evicted == []

    def test_get_context_messages(self):
        mgr = MemoryManager(node_id="root")
        mgr.add_message("user", "Hello", token_count=5)
        messages = mgr.get_context_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_add_message_item(self):
        mgr = MemoryManager(node_id="root")
        item = MessageItem(role="user", content="Hi", token_count=3)
        evicted = mgr.add_message_item(item)
        assert evicted == []
        items = mgr.get_message_items()
        assert len(items) == 1
        assert items[0].content == "Hi"

    def test_get_message_items(self):
        mgr = MemoryManager(node_id="root")
        mgr.add_message("user", "A", token_count=3)
        mgr.add_message("assistant", "B", token_count=3)
        items = mgr.get_message_items()
        assert len(items) == 2
        assert items[0].role == "user"
        assert items[1].role == "assistant"


class TestMemoryManagerL2Proxy:
    """测试 L2 工作记忆 API 代理"""

    def test_add_working_memory(self):
        mgr = MemoryManager(node_id="root")
        entry = WorkingMemoryEntry(
            content="important fact",
            entry_type=MemoryType.FACT,
            importance=0.8,
            token_count=10,
        )
        evicted = mgr.add_working_memory(entry)
        assert evicted == []

    def test_get_working_memory(self):
        mgr = MemoryManager(node_id="root")
        entry = WorkingMemoryEntry(
            content="fact",
            entry_type=MemoryType.FACT,
            importance=0.8,
            token_count=5,
        )
        mgr.add_working_memory(entry)
        entries = mgr.get_working_memory()
        assert len(entries) == 1
        assert entries[0].content == "fact"


class TestMemoryManagerL3Proxy:
    """测试 L3 持久记忆 API 代理"""

    async def test_save_persistent_no_store(self):
        mgr = MemoryManager(node_id="root")
        record = MemoryRecord(content="test")
        result = await mgr.save_persistent(record)
        assert result is None  # 无 L3 存储

    async def test_search_persistent_no_store(self):
        mgr = MemoryManager(node_id="root")
        results = await mgr.search_persistent("query")
        assert results == []

    async def test_search_no_store(self):
        mgr = MemoryManager(node_id="root")
        results = await mgr.search("query")
        assert isinstance(results, list)

    async def test_set_memory_store(self):
        mgr = MemoryManager(node_id="root")
        store = MagicMock()
        mgr.set_memory_store(store)
        assert mgr.memory.l3 is store


class TestMemoryManagerStats:
    def test_get_stats(self):
        mgr = MemoryManager(node_id="root")
        stats = mgr.get_stats()
        assert stats["node_id"] == "root"
        assert stats["children_count"] == 0
        assert stats["has_parent"] is False
        assert stats["context_count"] == 0
        assert "l1_token_usage" in stats
        assert "l2_token_usage" in stats

    def test_get_stats_with_messages(self):
        mgr = MemoryManager(node_id="root")
        mgr.add_message("user", "Hello", token_count=5)
        stats = mgr.get_stats()
        assert stats["l1_message_count"] == 1
        assert stats["l1_token_usage"] == 5


class TestMemoryManagerSnapshot:
    def test_export_snapshot(self):
        mgr = MemoryManager(node_id="root")
        snapshot = mgr.export_snapshot()
        assert snapshot["node_id"] == "root"
        assert "l1_items" in snapshot
        assert "l2_items" in snapshot
        assert "context" in snapshot

    def test_export_with_messages(self):
        mgr = MemoryManager(node_id="root")
        mgr.add_message("user", "Hello", token_count=5)
        snapshot = mgr.export_snapshot()
        assert len(snapshot["l1_items"]) == 1
        assert snapshot["l1_items"][0]["role"] == "user"
        assert snapshot["l1_items"][0]["content"] == "Hello"

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

    def test_restore_l1_messages(self):
        mgr = MemoryManager(node_id="root")
        snapshot = {
            "l1_items": [
                {"role": "user", "content": "Hello", "token_count": 5, "message_id": "m1"},
            ],
            "l2_items": [],
            "context": {},
        }
        mgr.restore_snapshot(snapshot)
        items = mgr.get_message_items()
        assert len(items) == 1
        assert items[0].role == "user"
        assert items[0].content == "Hello"


class TestMemoryManagerSession:
    async def test_end_session(self):
        mgr = MemoryManager(node_id="root")
        mgr.add_message("user", "Hello", token_count=5)
        count = await mgr.end_session()
        # 无 L3 存储，不会持久化
        assert count == 0

    async def test_flush_pending(self):
        mgr = MemoryManager(node_id="root")
        count = await mgr.flush_pending()
        assert count == 0
