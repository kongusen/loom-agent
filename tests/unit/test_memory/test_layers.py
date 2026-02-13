"""
Tests for loom/memory/layers_merged.py — MessageWindow (L1) & WorkingMemoryLayer (L2)
"""

from loom.memory.layers_merged import MessageWindow, WorkingMemoryLayer
from loom.memory.types import MemoryType, MessageItem, WorkingMemoryEntry

# ==================== MessageWindow (L1) ====================


class TestMessageWindowBasic:
    def test_init_defaults(self):
        w = MessageWindow()
        assert w.token_budget == 8000
        assert w.token_usage() == 0
        assert w.size() == 0

    def test_init_custom_budget(self):
        w = MessageWindow(token_budget=1000)
        assert w.token_budget == 1000

    def test_append_single(self):
        w = MessageWindow()
        item = MessageItem(role="user", content="Hello", token_count=5)
        evicted = w.append(item)
        assert evicted == []
        assert w.size() == 1
        assert w.token_usage() == 5

    def test_append_message(self):
        w = MessageWindow()
        evicted = w.append_message("user", "Hello", token_count=5)
        assert evicted == []
        assert w.size() == 1

    def test_get_messages(self):
        w = MessageWindow()
        w.append_message("user", "Hello", token_count=5)
        w.append_message("assistant", "Hi there", token_count=4)
        msgs = w.get_messages()
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "Hello"}
        assert msgs[1] == {"role": "assistant", "content": "Hi there"}

    def test_get_items(self):
        w = MessageWindow()
        w.append_message("user", "A", token_count=3)
        items = w.get_items()
        assert len(items) == 1
        assert items[0].role == "user"
        assert items[0].content == "A"

    def test_get_recent(self):
        w = MessageWindow()
        for i in range(5):
            w.append_message("user", f"msg-{i}", token_count=3)
        recent = w.get_recent(2)
        assert len(recent) == 2
        assert recent[0].content == "msg-3"
        assert recent[1].content == "msg-4"

    def test_get_recent_more_than_size(self):
        w = MessageWindow()
        w.append_message("user", "only", token_count=3)
        recent = w.get_recent(10)
        assert len(recent) == 1

    def test_clear(self):
        w = MessageWindow()
        w.append_message("user", "Hello", token_count=5)
        w.clear()
        assert w.size() == 0
        assert w.token_usage() == 0

    def test_set_token_budget(self):
        w = MessageWindow(token_budget=100)
        w.token_budget = 200
        assert w.token_budget == 200


class TestMessageWindowEviction:
    def test_basic_eviction(self):
        w = MessageWindow(token_budget=10)
        w.append_message("user", "A", token_count=6)
        evicted = w.append_message("user", "B", token_count=6)
        assert len(evicted) == 1
        assert evicted[0].content == "A"
        assert w.size() == 1
        assert w.token_usage() == 6

    def test_system_protected(self):
        """system 消息不被驱逐"""
        w = MessageWindow(token_budget=15)
        w.append_message("system", "You are helpful", token_count=5)
        w.append_message("user", "A", token_count=6)
        evicted = w.append_message("user", "B", token_count=6)
        # user "A" should be evicted, not system
        assert len(evicted) == 1
        assert evicted[0].role == "user"
        assert evicted[0].content == "A"
        # system + B remain
        assert w.size() == 2

    def test_eviction_callback(self):
        w = MessageWindow(token_budget=10)
        evicted_log = []
        w.on_eviction(lambda msgs: evicted_log.extend(msgs))

        w.append_message("user", "A", token_count=6)
        w.append_message("user", "B", token_count=6)

        assert len(evicted_log) == 1
        assert evicted_log[0].content == "A"

    def test_multiple_evictions(self):
        w = MessageWindow(token_budget=10)
        w.append_message("user", "A", token_count=4)
        w.append_message("user", "B", token_count=4)
        # 4+4=8, +5=13 > 10, evict A → 4+5=9 <= 10
        evicted = w.append_message("user", "C", token_count=5)
        assert len(evicted) == 1
        assert evicted[0].content == "A"
        assert w.size() == 2


class TestMessageWindowPairedEviction:
    def test_assistant_tool_calls_paired(self):
        """驱逐 assistant(tool_calls) 时同时驱逐对应的 tool result"""
        w = MessageWindow(token_budget=30)

        # assistant with tool_calls
        w.append(MessageItem(
            role="assistant",
            content=None,
            token_count=5,
            tool_calls=[{"id": "tc1", "function": {"name": "search", "arguments": "{}"}}],
        ))
        # tool result
        w.append(MessageItem(
            role="tool",
            content="result",
            token_count=5,
            tool_call_id="tc1",
            tool_name="search",
        ))
        # user message
        w.append_message("user", "thanks", token_count=5)

        assert w.size() == 3
        assert w.token_usage() == 15

        # Add large message to trigger eviction
        evicted = w.append_message("user", "big message", token_count=20)

        # Both assistant(tool_calls) and tool result should be evicted together
        assert len(evicted) == 2
        roles = {e.role for e in evicted}
        assert "assistant" in roles
        assert "tool" in roles

    def test_tool_result_triggers_paired_eviction(self):
        """驱逐 tool result 时同时驱逐对应的 assistant(tool_calls)"""
        w = MessageWindow(token_budget=20)

        # user message first (will be evicted first since it's oldest non-system)
        w.append_message("user", "do search", token_count=3)

        # assistant with tool_calls
        w.append(MessageItem(
            role="assistant",
            content=None,
            token_count=5,
            tool_calls=[{"id": "tc1", "function": {"name": "search", "arguments": "{}"}}],
        ))
        # tool result
        w.append(MessageItem(
            role="tool",
            content="result",
            token_count=5,
            tool_call_id="tc1",
        ))

        assert w.token_usage() == 13

        # Trigger eviction — user msg evicted first (single)
        evicted = w.append_message("user", "big", token_count=10)
        # 13 + 10 = 23 > 20, evict "do search" (3) → 20, 20 <= 20
        assert len(evicted) == 1
        assert evicted[0].content == "do search"


# ==================== WorkingMemoryLayer (L2) ====================


class TestWorkingMemoryLayerBasic:
    def test_init_defaults(self):
        l2 = WorkingMemoryLayer()
        assert l2.token_budget == 16000
        assert l2.token_usage() == 0
        assert l2.size() == 0

    def test_init_custom_budget(self):
        l2 = WorkingMemoryLayer(token_budget=500)
        assert l2.token_budget == 500

    def test_add_entry(self):
        l2 = WorkingMemoryLayer()
        entry = WorkingMemoryEntry(
            content="important fact",
            entry_type=MemoryType.FACT,
            importance=0.8,
            token_count=10,
        )
        evicted = l2.add(entry)
        assert evicted == []
        assert l2.size() == 1
        assert l2.token_usage() == 10

    def test_get_entries_sorted_by_importance(self):
        l2 = WorkingMemoryLayer()
        l2.add(WorkingMemoryEntry(content="low", importance=0.3, token_count=5))
        l2.add(WorkingMemoryEntry(content="high", importance=0.9, token_count=5))
        l2.add(WorkingMemoryEntry(content="mid", importance=0.6, token_count=5))

        entries = l2.get_entries()
        assert entries[0].content == "high"
        assert entries[1].content == "mid"
        assert entries[2].content == "low"

    def test_get_entries_with_limit(self):
        l2 = WorkingMemoryLayer()
        for i in range(5):
            l2.add(WorkingMemoryEntry(content=f"e{i}", importance=i * 0.2, token_count=3))
        entries = l2.get_entries(limit=2)
        assert len(entries) == 2

    def test_get_by_type(self):
        l2 = WorkingMemoryLayer()
        l2.add(WorkingMemoryEntry(content="fact1", entry_type=MemoryType.FACT, token_count=5))
        l2.add(WorkingMemoryEntry(content="decision1", entry_type=MemoryType.DECISION, token_count=5))
        l2.add(WorkingMemoryEntry(content="fact2", entry_type=MemoryType.FACT, token_count=5))

        facts = l2.get_by_type("fact")
        assert len(facts) == 2
        decisions = l2.get_by_type("decision")
        assert len(decisions) == 1

    def test_find_by_id(self):
        l2 = WorkingMemoryLayer()
        entry = WorkingMemoryEntry(content="findme", token_count=5)
        l2.add(entry)
        found = l2.find(entry.entry_id)
        assert found is not None
        assert found.content == "findme"

    def test_find_missing(self):
        l2 = WorkingMemoryLayer()
        assert l2.find("nonexistent") is None

    def test_remove(self):
        l2 = WorkingMemoryLayer()
        entry = WorkingMemoryEntry(content="removeme", token_count=5)
        l2.add(entry)
        assert l2.size() == 1
        removed = l2.remove(entry.entry_id)
        assert removed is True
        assert l2.size() == 0
        assert l2.token_usage() == 0

    def test_remove_missing(self):
        l2 = WorkingMemoryLayer()
        assert l2.remove("nonexistent") is False

    def test_clear(self):
        l2 = WorkingMemoryLayer()
        l2.add(WorkingMemoryEntry(content="x", token_count=5))
        l2.clear()
        assert l2.size() == 0
        assert l2.token_usage() == 0

    def test_set_token_budget(self):
        l2 = WorkingMemoryLayer(token_budget=100)
        l2.token_budget = 200
        assert l2.token_budget == 200


class TestWorkingMemoryLayerEviction:
    def test_evict_lowest_importance(self):
        l2 = WorkingMemoryLayer(token_budget=15)
        l2.add(WorkingMemoryEntry(content="low", importance=0.2, token_count=8))
        l2.add(WorkingMemoryEntry(content="high", importance=0.9, token_count=5))

        # Adding this should evict "low" (importance=0.2)
        evicted = l2.add(WorkingMemoryEntry(content="mid", importance=0.5, token_count=8))
        assert len(evicted) == 1
        assert evicted[0].content == "low"

    def test_reject_if_new_entry_lowest(self):
        """新条目 importance 最低时不添加"""
        l2 = WorkingMemoryLayer(token_budget=10)
        l2.add(WorkingMemoryEntry(content="high", importance=0.9, token_count=8))

        evicted = l2.add(WorkingMemoryEntry(content="lowest", importance=0.1, token_count=8))
        assert evicted == []
        assert l2.size() == 1

    def test_eviction_callback(self):
        l2 = WorkingMemoryLayer(token_budget=10)
        evicted_log = []
        l2.on_eviction(lambda entries: evicted_log.extend(entries))

        l2.add(WorkingMemoryEntry(content="low", importance=0.2, token_count=8))
        l2.add(WorkingMemoryEntry(content="high", importance=0.9, token_count=8))

        assert len(evicted_log) == 1
        assert evicted_log[0].content == "low"
