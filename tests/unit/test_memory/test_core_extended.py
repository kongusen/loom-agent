"""
LoomMemory Extended Unit Tests — 三层记忆系统

测试 LoomMemory 的完整 API：
- L1 消息管理 (add_message, get_context_messages)
- L2 工作记忆 (add_working_memory, get_working_memory)
- L3 持久记忆 (save_persistent, search_persistent)
- 跨层搜索 (search)
- 驱逐管线 (L1→L2→L3)
- Session 生命周期 (end_session, flush_pending)
- 配置与状态 (get_stats, clear_all, close)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.memory.core import LoomMemory
from loom.memory.types import (
    MemoryRecord,
    MemoryType,
    MessageItem,
    WorkingMemoryEntry,
)

# ==================== L1: Message API ====================


class TestLoomMemoryL1:
    def test_add_message(self):
        mem = LoomMemory(node_id="test")
        evicted = mem.add_message("user", "Hello", token_count=5)
        assert evicted == []
        assert mem.l1.size() == 1

    def test_add_message_auto_token_count(self):
        mem = LoomMemory(node_id="test")
        mem.add_message("user", "Hello world")
        items = mem.get_message_items()
        assert len(items) == 1
        assert items[0].token_count > 0  # auto-calculated

    def test_add_message_item(self):
        mem = LoomMemory(node_id="test")
        item = MessageItem(role="user", content="Hi", token_count=3)
        evicted = mem.add_message_item(item)
        assert evicted == []
        assert mem.l1.size() == 1

    def test_get_context_messages(self):
        mem = LoomMemory(node_id="test")
        mem.add_message("user", "Hello", token_count=5)
        mem.add_message("assistant", "Hi there", token_count=4)
        msgs = mem.get_context_messages()
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "Hello"}
        assert msgs[1] == {"role": "assistant", "content": "Hi there"}

    def test_get_message_items(self):
        mem = LoomMemory(node_id="test")
        mem.add_message("user", "A", token_count=3)
        items = mem.get_message_items()
        assert len(items) == 1
        assert items[0].role == "user"

    def test_session_id_injected_to_metadata(self):
        mem = LoomMemory(node_id="test", session_id="sess-1")
        mem.add_message("user", "Hello", token_count=5)
        items = mem.get_message_items()
        assert items[0].metadata.get("session_id") == "sess-1"

    def test_add_message_with_kwargs(self):
        mem = LoomMemory(node_id="test")
        mem.add_message(
            "tool",
            "result data",
            token_count=5,
            tool_call_id="tc1",
            tool_name="search",
        )
        items = mem.get_message_items()
        assert items[0].tool_call_id == "tc1"
        assert items[0].tool_name == "search"


# ==================== L2: Working Memory API ====================


class TestLoomMemoryL2:
    def test_add_working_memory(self):
        mem = LoomMemory(node_id="test")
        entry = WorkingMemoryEntry(
            content="important fact",
            entry_type=MemoryType.FACT,
            importance=0.8,
            token_count=10,
        )
        evicted = mem.add_working_memory(entry)
        assert evicted == []
        assert mem.l2.size() == 1

    def test_get_working_memory(self):
        mem = LoomMemory(node_id="test")
        mem.add_working_memory(WorkingMemoryEntry(
            content="fact1", importance=0.8, token_count=5,
        ))
        mem.add_working_memory(WorkingMemoryEntry(
            content="fact2", importance=0.5, token_count=5,
        ))
        entries = mem.get_working_memory()
        assert len(entries) == 2
        # sorted by importance desc
        assert entries[0].content == "fact1"

    def test_get_working_memory_with_limit(self):
        mem = LoomMemory(node_id="test")
        for i in range(5):
            mem.add_working_memory(WorkingMemoryEntry(
                content=f"e{i}", importance=i * 0.2, token_count=3,
            ))
        entries = mem.get_working_memory(limit=2)
        assert len(entries) == 2

    def test_get_working_memory_by_type(self):
        mem = LoomMemory(node_id="test")
        mem.add_working_memory(WorkingMemoryEntry(
            content="fact", entry_type=MemoryType.FACT, token_count=5,
        ))
        mem.add_working_memory(WorkingMemoryEntry(
            content="decision", entry_type=MemoryType.DECISION, token_count=5,
        ))
        facts = mem.get_working_memory(entry_type="fact")
        assert len(facts) == 1
        assert facts[0].content == "fact"


# ==================== L3: Persistent Memory API ====================


class TestLoomMemoryL3:
    @pytest.mark.asyncio
    async def test_save_persistent_no_store(self):
        mem = LoomMemory(node_id="test")
        record = MemoryRecord(content="test")
        result = await mem.save_persistent(record)
        assert result is None

    @pytest.mark.asyncio
    async def test_save_persistent_with_store(self):
        mem = LoomMemory(node_id="test", user_id="u1")
        store = MagicMock()
        store.save = AsyncMock(return_value="rec-1")
        mem.set_memory_store(store)

        record = MemoryRecord(content="test")
        result = await mem.save_persistent(record)
        assert result == "rec-1"
        store.save.assert_called_once()
        # user_id should be injected
        saved_record = store.save.call_args[0][0]
        assert saved_record.user_id == "u1"

    @pytest.mark.asyncio
    async def test_search_persistent_no_store(self):
        mem = LoomMemory(node_id="test")
        results = await mem.search_persistent("query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_persistent_with_store(self):
        mem = LoomMemory(node_id="test", user_id="u1")
        store = MagicMock()
        store.query_by_text = AsyncMock(return_value=[
            MemoryRecord(content="match"),
        ])
        mem.set_memory_store(store)

        results = await mem.search_persistent("query")
        assert len(results) == 1
        store.query_by_text.assert_called_once_with(
            query="query", limit=5, user_id="u1",
        )

    @pytest.mark.asyncio
    async def test_search_persistent_by_vector_no_store(self):
        mem = LoomMemory(node_id="test")
        results = await mem.search_persistent_by_vector([0.1, 0.2])
        assert results == []

    @pytest.mark.asyncio
    async def test_search_persistent_by_vector_with_store(self):
        mem = LoomMemory(node_id="test")
        store = MagicMock()
        store.query_by_vector = AsyncMock(return_value=[
            MemoryRecord(content="vec match"),
        ])
        mem.set_memory_store(store)

        results = await mem.search_persistent_by_vector([0.1, 0.2])
        assert len(results) == 1


# ==================== Cross-layer Search ====================


class TestLoomMemorySearch:
    @pytest.mark.asyncio
    async def test_search_l1_text_match(self):
        mem = LoomMemory(node_id="test")
        mem.add_message("user", "Python is great", token_count=5)
        results = await mem.search("Python")
        assert any(r["tier"] == "L1" for r in results)

    @pytest.mark.asyncio
    async def test_search_l2_text_match(self):
        mem = LoomMemory(node_id="test")
        mem.add_working_memory(WorkingMemoryEntry(
            content="Python best practices",
            importance=0.8,
            token_count=5,
        ))
        results = await mem.search("Python")
        assert any(r["tier"] == "L2" for r in results)

    @pytest.mark.asyncio
    async def test_search_l2_tag_match(self):
        mem = LoomMemory(node_id="test")
        mem.add_working_memory(WorkingMemoryEntry(
            content="some entry",
            importance=0.8,
            token_count=5,
            tags=["python", "coding"],
        ))
        results = await mem.search("python")
        assert any(r["tier"] == "L2" for r in results)

    @pytest.mark.asyncio
    async def test_search_l3_with_store(self):
        mem = LoomMemory(node_id="test")
        store = MagicMock()
        store.query_by_text = AsyncMock(return_value=[
            MemoryRecord(content="persistent match", importance=0.7),
        ])
        mem.set_memory_store(store)

        results = await mem.search("match")
        assert any(r["tier"] == "L3" for r in results)

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        mem = LoomMemory(node_id="test")
        results = await mem.search("nonexistent_xyz")
        assert results == []


# ==================== Eviction Pipeline (L1→L2→L3) ====================


class TestLoomMemoryEvictionPipeline:
    def test_l1_eviction_triggers_l2_extraction(self):
        """L1 驱逐消息时，默认提取器应将摘要写入 L2"""
        mem = LoomMemory(node_id="test", l1_token_budget=10, l2_importance_threshold=0.0)

        mem.add_message("user", "Hello world", token_count=6)
        # This should trigger eviction of "Hello world"
        mem.add_message("user", "Second message", token_count=6)

        # Default extractor should have created an L2 entry
        entries = mem.get_working_memory()
        assert len(entries) >= 1
        assert "User: Hello world" in entries[0].content

    def test_l1_eviction_with_custom_extractor(self):
        """自定义 L1→L2 提取器"""
        extracted = []

        def custom_extractor(evicted, token_counter):
            for msg in evicted:
                extracted.append(msg.content)
            return [WorkingMemoryEntry(
                content="custom extraction",
                importance=0.9,
                token_count=5,
            )]

        mem = LoomMemory(
            node_id="test",
            l1_token_budget=10,
            eviction_extractor=custom_extractor,
        )
        mem.add_message("user", "Hello", token_count=6)
        mem.add_message("user", "World", token_count=6)

        assert len(extracted) > 0
        entries = mem.get_working_memory()
        assert any(e.content == "custom extraction" for e in entries)

    def test_l2_eviction_queues_l3_records(self):
        """L2 驱逐时，记录应进入 L3 待写入队列"""
        mem = LoomMemory(node_id="test", l2_token_budget=10)

        # Add high-importance entry first
        mem.add_working_memory(WorkingMemoryEntry(
            content="high", importance=0.9, token_count=8,
        ))
        # Add another high-importance entry to trigger eviction of something
        mem.add_working_memory(WorkingMemoryEntry(
            content="higher", importance=0.95, token_count=8,
        ))

        # Check pending L3 records
        stats = mem.get_stats()
        assert stats["l3_pending_count"] >= 1

    def test_l2_eviction_with_custom_summarizer(self):
        """自定义 L2→L3 摘要器"""
        summarized = []

        def custom_summarizer(evicted):
            for entry in evicted:
                summarized.append(entry.content)
            return [MemoryRecord(content="custom summary")]

        mem = LoomMemory(
            node_id="test",
            l2_token_budget=10,
            persistence_summarizer=custom_summarizer,
        )
        mem.add_working_memory(WorkingMemoryEntry(
            content="high", importance=0.9, token_count=8,
        ))
        mem.add_working_memory(WorkingMemoryEntry(
            content="higher", importance=0.95, token_count=8,
        ))

        assert len(summarized) > 0


# ==================== Session Lifecycle ====================


class TestLoomMemorySession:
    @pytest.mark.asyncio
    async def test_end_session_no_store(self):
        mem = LoomMemory(node_id="test")
        mem.add_message("user", "Hello", token_count=5)
        mem.add_working_memory(WorkingMemoryEntry(
            content="fact", importance=0.8, token_count=5,
        ))
        count = await mem.end_session()
        assert count == 0  # no L3 store
        assert mem.l1.size() == 0
        assert mem.l2.size() == 0

    @pytest.mark.asyncio
    async def test_end_session_with_store(self):
        mem = LoomMemory(node_id="test")
        store = MagicMock()
        store.save = AsyncMock(return_value="rec-1")
        mem.set_memory_store(store)

        mem.add_working_memory(WorkingMemoryEntry(
            content="fact", importance=0.8, token_count=5,
        ))
        count = await mem.end_session()
        assert count >= 1
        assert mem.l1.size() == 0
        assert mem.l2.size() == 0

    @pytest.mark.asyncio
    async def test_flush_pending_no_store(self):
        mem = LoomMemory(node_id="test")
        count = await mem.flush_pending()
        assert count == 0

    @pytest.mark.asyncio
    async def test_flush_pending_with_store(self):
        mem = LoomMemory(node_id="test", l2_token_budget=10)
        store = MagicMock()
        store.save = AsyncMock(return_value="rec-1")
        mem.set_memory_store(store)

        # Force L2 eviction to create pending records
        mem.add_working_memory(WorkingMemoryEntry(
            content="high", importance=0.9, token_count=8,
        ))
        mem.add_working_memory(WorkingMemoryEntry(
            content="higher", importance=0.95, token_count=8,
        ))

        count = await mem.flush_pending()
        assert count >= 1


# ==================== Configuration & State ====================


class TestLoomMemoryConfig:
    def test_init_defaults(self):
        mem = LoomMemory(node_id="test")
        assert mem.node_id == "test"
        assert mem.user_id is None
        assert mem.session_id is None
        assert mem.l1.token_budget == 8000
        assert mem.l2.token_budget == 16000
        assert mem.l3 is None

    def test_init_custom(self):
        mem = LoomMemory(
            node_id="test",
            l1_token_budget=4000,
            l2_token_budget=8000,
            user_id="u1",
            session_id="s1",
        )
        assert mem.l1.token_budget == 4000
        assert mem.l2.token_budget == 8000
        assert mem.user_id == "u1"
        assert mem.session_id == "s1"

    def test_set_memory_store(self):
        mem = LoomMemory(node_id="test")
        store = MagicMock()
        mem.set_memory_store(store)
        assert mem.l3 is store

    def test_set_eviction_extractor(self):
        mem = LoomMemory(node_id="test")

        def custom(evicted, tc):
            return []

        mem.set_eviction_extractor(custom)
        assert mem._eviction_extractor is custom

    def test_set_persistence_summarizer(self):
        mem = LoomMemory(node_id="test")

        def custom(evicted):
            return []

        mem.set_persistence_summarizer(custom)
        assert mem._persistence_summarizer is custom

    def test_token_counter_property(self):
        mem = LoomMemory(node_id="test")
        assert mem.token_counter is not None


class TestLoomMemoryStats:
    def test_get_stats_empty(self):
        mem = LoomMemory(node_id="test", user_id="u1", session_id="s1")
        stats = mem.get_stats()
        assert stats["node_id"] == "test"
        assert stats["user_id"] == "u1"
        assert stats["session_id"] == "s1"
        assert stats["l1_token_usage"] == 0
        assert stats["l1_message_count"] == 0
        assert stats["l2_token_usage"] == 0
        assert stats["l2_entry_count"] == 0
        assert stats["l3_enabled"] is False
        assert stats["l3_pending_count"] == 0

    def test_get_stats_with_data(self):
        mem = LoomMemory(node_id="test")
        mem.add_message("user", "Hello", token_count=5)
        mem.add_working_memory(WorkingMemoryEntry(
            content="fact", importance=0.8, token_count=10,
        ))
        stats = mem.get_stats()
        assert stats["l1_token_usage"] == 5
        assert stats["l1_message_count"] == 1
        assert stats["l2_token_usage"] == 10
        assert stats["l2_entry_count"] == 1


class TestLoomMemoryClearClose:
    def test_clear_all(self):
        mem = LoomMemory(node_id="test")
        mem.add_message("user", "Hello", token_count=5)
        mem.add_working_memory(WorkingMemoryEntry(
            content="fact", token_count=5,
        ))
        mem.clear_all()
        assert mem.l1.size() == 0
        assert mem.l2.size() == 0

    def test_close(self):
        mem = LoomMemory(node_id="test")
        mem.add_message("user", "Hello", token_count=5)
        mem.close()
        assert mem.l1.size() == 0
        assert mem.l2.size() == 0
