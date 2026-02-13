"""
Tests for loom/memory/types.py — 三层架构类型定义

覆盖：MemoryTier, MemoryType, MemoryStatus, FactType,
      MessageItem, WorkingMemoryEntry, MemoryRecord, MemoryQuery
"""

from datetime import datetime

from loom.memory.types import (
    FactType,
    MemoryQuery,
    MemoryRecord,
    MemoryStatus,
    MemoryTier,
    MemoryType,
    MessageItem,
    WorkingMemoryEntry,
)

# ==================== Enums ====================


class TestMemoryTier:
    def test_values(self):
        assert MemoryTier.L1_WINDOW.value == 1
        assert MemoryTier.L2_WORKING.value == 2
        assert MemoryTier.L3_PERSISTENT.value == 3

    def test_ordering(self):
        assert MemoryTier.L1_WINDOW.value < MemoryTier.L2_WORKING.value
        assert MemoryTier.L2_WORKING.value < MemoryTier.L3_PERSISTENT.value

    def test_member_count(self):
        assert len(MemoryTier) == 3


class TestMemoryType:
    def test_all_values(self):
        expected = {
            "message", "thought", "tool_call", "tool_result",
            "plan", "fact", "decision", "summary", "context",
        }
        actual = {m.value for m in MemoryType}
        assert actual == expected

    def test_lookup_by_value(self):
        assert MemoryType("fact") is MemoryType.FACT
        assert MemoryType("summary") is MemoryType.SUMMARY


class TestMemoryStatus:
    def test_all_values(self):
        expected = {"active", "archived", "summarized", "evicted"}
        actual = {s.value for s in MemoryStatus}
        assert actual == expected


class TestFactType:
    def test_all_values(self):
        expected = {
            "api_schema", "user_preference", "domain_knowledge",
            "tool_usage", "error_pattern", "best_practice",
            "conversation_summary",
        }
        actual = {f.value for f in FactType}
        assert actual == expected


# ==================== MessageItem ====================


class TestMessageItem:
    def test_defaults(self):
        item = MessageItem(role="user", content="Hello")
        assert item.role == "user"
        assert item.content == "Hello"
        assert item.token_count == 0
        assert item.message_id  # auto-generated UUID
        assert item.tool_call_id is None
        assert item.tool_name is None
        assert item.tool_calls is None
        assert isinstance(item.created_at, datetime)
        assert item.metadata == {}

    def test_unique_ids(self):
        a = MessageItem(role="user", content="a")
        b = MessageItem(role="user", content="b")
        assert a.message_id != b.message_id

    def test_to_message_user(self):
        item = MessageItem(role="user", content="Hi")
        msg = item.to_message()
        assert msg == {"role": "user", "content": "Hi"}

    def test_to_message_assistant_with_tool_calls(self):
        calls = [{"id": "tc1", "function": {"name": "search", "arguments": "{}"}}]
        item = MessageItem(role="assistant", content=None, tool_calls=calls)
        msg = item.to_message()
        assert msg["role"] == "assistant"
        assert msg["tool_calls"] == calls
        assert "content" not in msg

    def test_to_message_tool(self):
        item = MessageItem(
            role="tool",
            content="result data",
            tool_call_id="tc1",
            tool_name="search",
        )
        msg = item.to_message()
        assert msg["role"] == "tool"
        assert msg["content"] == "result data"
        assert msg["tool_call_id"] == "tc1"
        assert msg["name"] == "search"

    def test_from_message_user(self):
        raw = {"role": "user", "content": "Hello"}
        item = MessageItem.from_message(raw, token_count=5)
        assert item.role == "user"
        assert item.content == "Hello"
        assert item.token_count == 5

    def test_from_message_tool(self):
        raw = {
            "role": "tool",
            "content": "ok",
            "tool_call_id": "tc1",
            "name": "run",
        }
        item = MessageItem.from_message(raw)
        assert item.tool_call_id == "tc1"
        assert item.tool_name == "run"

    def test_from_message_defaults(self):
        item = MessageItem.from_message({})
        assert item.role == "user"
        assert item.content is None
        assert item.token_count == 0

    def test_dict_content(self):
        item = MessageItem(role="user", content={"type": "image", "url": "x"})
        msg = item.to_message()
        assert msg["content"] == {"type": "image", "url": "x"}

    def test_metadata(self):
        item = MessageItem(role="user", content="hi", metadata={"session": "s1"})
        assert item.metadata["session"] == "s1"


# ==================== WorkingMemoryEntry ====================


class TestWorkingMemoryEntry:
    def test_defaults(self):
        entry = WorkingMemoryEntry(content="important fact", token_count=10)
        assert entry.content == "important fact"
        assert entry.entry_type == MemoryType.FACT
        assert entry.importance == 0.5
        assert entry.token_count == 10
        assert entry.tags == []
        assert entry.source_message_ids == []
        assert entry.session_id is None
        assert entry.access_count == 0
        assert entry.entry_id  # auto-generated

    def test_custom_fields(self):
        entry = WorkingMemoryEntry(
            content="user prefers dark mode",
            entry_type=MemoryType.DECISION,
            importance=0.9,
            token_count=8,
            tags=["preference", "ui"],
            session_id="sess-1",
        )
        assert entry.entry_type == MemoryType.DECISION
        assert entry.importance == 0.9
        assert entry.tags == ["preference", "ui"]
        assert entry.session_id == "sess-1"

    def test_update_access(self):
        entry = WorkingMemoryEntry(content="x", token_count=1)
        assert entry.access_count == 0
        entry.update_access()
        assert entry.access_count == 1
        entry.update_access()
        assert entry.access_count == 2

    def test_unique_ids(self):
        a = WorkingMemoryEntry(content="a", token_count=1)
        b = WorkingMemoryEntry(content="b", token_count=1)
        assert a.entry_id != b.entry_id


# ==================== MemoryRecord ====================


class TestMemoryRecord:
    def test_defaults(self):
        record = MemoryRecord(content="summary text")
        assert record.content == "summary text"
        assert record.user_id is None
        assert record.session_id is None
        assert record.importance == 0.5
        assert record.tags == []
        assert record.embedding is None
        assert record.source_entry_ids == []
        assert record.record_id  # auto-generated

    def test_custom_fields(self):
        record = MemoryRecord(
            content="user likes Python",
            user_id="u1",
            session_id="s1",
            importance=0.8,
            tags=["preference"],
            embedding=[0.1, 0.2, 0.3],
            source_entry_ids=["e1", "e2"],
        )
        assert record.user_id == "u1"
        assert record.session_id == "s1"
        assert record.importance == 0.8
        assert record.embedding == [0.1, 0.2, 0.3]
        assert record.source_entry_ids == ["e1", "e2"]

    def test_unique_ids(self):
        a = MemoryRecord(content="a")
        b = MemoryRecord(content="b")
        assert a.record_id != b.record_id

    def test_mutable_user_id(self):
        record = MemoryRecord(content="x")
        assert record.user_id is None
        record.user_id = "u1"
        assert record.user_id == "u1"


# ==================== MemoryQuery ====================


class TestMemoryQuery:
    def test_defaults(self):
        q = MemoryQuery(query="search term")
        assert q.query == "search term"
        assert q.tier is None
        assert q.type is None
        assert q.limit == 10
        assert q.min_importance == 0.0
        assert q.user_id is None
        assert q.session_id is None

    def test_custom_fields(self):
        q = MemoryQuery(
            query="Python",
            tier=MemoryTier.L2_WORKING,
            type=MemoryType.FACT,
            limit=5,
            min_importance=0.3,
            user_id="u1",
            session_id="s1",
        )
        assert q.tier == MemoryTier.L2_WORKING
        assert q.type == MemoryType.FACT
        assert q.limit == 5
        assert q.min_importance == 0.3
