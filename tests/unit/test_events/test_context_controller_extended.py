"""
Tests for ContextController - extended coverage

Covers: session management, L3 aggregation, L4 persistence,
trigger_promotion, aggregate_context, distribute_task,
distribute_filtered, share_context, get_shared_l3_context,
_allocate_budget, _collect_from_session, _task_to_content, _estimate_tokens
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.events.context_controller import ContextController
from loom.runtime import Task, TaskStatus


def _make_session(session_id="s1", active=True):
    s = MagicMock()
    s.session_id = session_id
    s.is_active = active
    s.memory = MagicMock()
    s.memory.get_message_items = MagicMock(return_value=[])
    s.memory.get_working_memory = MagicMock(return_value=[])
    s.memory.add_message = MagicMock()
    s.memory.get_stats = MagicMock(return_value={})
    s.add_task = MagicMock()
    return s


def _make_task(action="node.thinking", content="hello", task_id="t1"):
    return Task(
        taskId=task_id,
        action=action,
        parameters={"content": content},
        status=TaskStatus.COMPLETED,
    )


def _make_entry(entry_id="e1", content="hello", importance=0.8):
    e = MagicMock()
    e.entry_id = entry_id
    e.content = content
    e.importance = importance
    e.token_count = max(1, len(content) // 4)
    e.tags = []
    e.session_id = None
    return e


def _make_msg_item(message_id="m1", role="assistant", content="hello", token_count=None):
    m = MagicMock()
    m.message_id = message_id
    m.role = role
    m.content = content
    m.token_count = token_count or max(1, len(content) // 4)
    return m


# ==================== Session Management ====================


class TestSessionManagement:
    def test_register_session(self):
        cc = ContextController()
        s = _make_session("s1")
        cc.register_session(s)
        assert "s1" in cc.session_ids
        assert cc.get_session("s1") is s

    def test_unregister_session(self):
        cc = ContextController()
        s = _make_session("s1")
        cc.register_session(s)
        cc.unregister_session("s1")
        assert "s1" not in cc.session_ids

    def test_unregister_nonexistent(self):
        cc = ContextController()
        cc.unregister_session("nope")  # should not raise

    def test_get_session_missing(self):
        cc = ContextController()
        assert cc.get_session("missing") is None

    def test_session_ids_empty(self):
        cc = ContextController()
        assert cc.session_ids == []

    def test_multiple_sessions(self):
        cc = ContextController()
        for i in range(3):
            cc.register_session(_make_session(f"s{i}"))
        assert len(cc.session_ids) == 3


# ==================== L3 Storage ====================


class TestL3Storage:
    def test_add_to_l3(self):
        cc = ContextController()
        cc.add_to_l3({"content": "summary1"})
        assert cc.l3_count == 1

    def test_get_l3_summaries(self):
        cc = ContextController()
        for i in range(5):
            cc.add_to_l3({"content": f"s{i}"})
        result = cc.get_l3_summaries(limit=3)
        assert len(result) == 3
        assert result[-1]["content"] == "s4"

    def test_l3_token_usage_initial(self):
        cc = ContextController()
        assert cc.l3_token_usage == 0


# ==================== aggregate_to_l3 ====================


class TestAggregateToL3:
    @pytest.mark.asyncio
    async def test_no_sessions(self):
        cc = ContextController()
        result = await cc.aggregate_to_l3()
        assert result is None

    @pytest.mark.asyncio
    async def test_with_l2_tasks(self):
        cc = ContextController()
        entry = _make_entry(entry_id="e1", content="important work", importance=0.8)
        s = _make_session("s1")
        s.memory.get_working_memory.return_value = [entry]
        cc.register_session(s)

        result = await cc.aggregate_to_l3(session_ids=["s1"])
        assert result is not None
        assert result["source_count"] == 1
        assert "s1" in result["session_ids"]

    @pytest.mark.asyncio
    async def test_with_summarizer(self):
        cc = ContextController()
        entry = _make_entry(entry_id="e1", content="data")
        s = _make_session("s1")
        s.memory.get_working_memory.return_value = [entry]
        cc.register_session(s)

        async def summarizer(contents):
            return "custom summary"

        result = await cc.aggregate_to_l3(summarizer=summarizer)
        assert result is not None
        assert result["content"] == "custom summary"

    @pytest.mark.asyncio
    async def test_inactive_session_skipped(self):
        cc = ContextController()
        s = _make_session("s1", active=False)
        cc.register_session(s)
        result = await cc.aggregate_to_l3()
        assert result is None

    @pytest.mark.asyncio
    async def test_budget_eviction(self):
        cc = ContextController()
        cc._l3_token_budget = 10  # very small budget

        entry = _make_entry(entry_id="e1", content="x" * 100)
        s = _make_session("s1")
        s.memory.get_working_memory.return_value = [entry]
        cc.register_session(s)

        # First aggregation fills budget
        await cc.aggregate_to_l3()
        # Second should evict old
        await cc.aggregate_to_l3()
        assert cc.l3_count >= 1


# ==================== L4 Persistence ====================


class TestL4Persistence:
    def test_set_l4_handlers(self):
        cc = ContextController()
        persist = AsyncMock()
        load = AsyncMock()
        cc.set_l4_handlers(persist, load)
        assert cc._l4_persist_handler is persist
        assert cc._l4_load_handler is load

    @pytest.mark.asyncio
    async def test_persist_no_handler(self):
        cc = ContextController()
        result = await cc.persist_to_l4({"content": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_persist_with_handler(self):
        cc = ContextController()
        persist = AsyncMock()
        cc.set_l4_handlers(persist)
        result = await cc.persist_to_l4({"content": "test"})
        assert result is True
        persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_none_uses_latest_l3(self):
        cc = ContextController()
        persist = AsyncMock()
        cc.set_l4_handlers(persist)
        cc.add_to_l3({"content": "latest"})
        result = await cc.persist_to_l4()
        assert result is True

    @pytest.mark.asyncio
    async def test_persist_none_no_l3(self):
        cc = ContextController()
        persist = AsyncMock()
        cc.set_l4_handlers(persist)
        result = await cc.persist_to_l4()
        assert result is False

    @pytest.mark.asyncio
    async def test_persist_handler_error(self):
        cc = ContextController()
        persist = AsyncMock(side_effect=RuntimeError("fail"))
        cc.set_l4_handlers(persist)
        result = await cc.persist_to_l4({"content": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_load_no_handler(self):
        cc = ContextController()
        result = await cc.load_from_l4()
        assert result == []

    @pytest.mark.asyncio
    async def test_load_with_handler(self):
        cc = ContextController()
        load = AsyncMock(return_value=[{"content": "loaded"}])
        cc.set_l4_handlers(AsyncMock(), load)
        result = await cc.load_from_l4("agent1")
        assert len(result) == 1
        load.assert_called_once_with("agent1")

    @pytest.mark.asyncio
    async def test_load_handler_error(self):
        cc = ContextController()
        load = AsyncMock(side_effect=RuntimeError("fail"))
        cc.set_l4_handlers(AsyncMock(), load)
        result = await cc.load_from_l4()
        assert result == []


# ==================== trigger_promotion ====================


class TestTriggerPromotion:
    @pytest.mark.asyncio
    async def test_basic_promotion(self):
        cc = ContextController()
        s = _make_session("s1")
        cc.register_session(s)

        result = await cc.trigger_promotion()
        assert result["sessions_processed"] == 1

    @pytest.mark.asyncio
    async def test_promotion_specific_session(self):
        cc = ContextController()
        s1 = _make_session("s1")
        s2 = _make_session("s2")
        cc.register_session(s1)
        cc.register_session(s2)

        result = await cc.trigger_promotion(session_id="s1")
        assert result["sessions_processed"] == 1

    @pytest.mark.asyncio
    async def test_promotion_with_l3_to_l4(self):
        cc = ContextController()
        persist = AsyncMock()
        cc.set_l4_handlers(persist)

        entry = _make_entry(entry_id="e1", content="data")
        s = _make_session("s1")
        s.memory.get_working_memory.return_value = [entry]
        cc.register_session(s)

        result = await cc.trigger_promotion(l3_to_l4=True)
        assert result["l3_to_l4"] is True


# ==================== distribute_task ====================


class TestDistributeTask:
    @pytest.mark.asyncio
    async def test_distribute_to_sessions(self):
        cc = ContextController()
        s1 = _make_session("s1")
        s2 = _make_session("s2")
        cc.register_session(s1)
        cc.register_session(s2)

        task = _make_task()
        result = await cc.distribute_task(task, ["s1", "s2"])
        assert len(result) == 2
        assert "s1" in result
        assert "s2" in result

    @pytest.mark.asyncio
    async def test_distribute_skips_inactive(self):
        cc = ContextController()
        s = _make_session("s1", active=False)
        cc.register_session(s)

        task = _make_task()
        result = await cc.distribute_task(task, ["s1"])
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_distribute_skips_missing(self):
        cc = ContextController()
        task = _make_task()
        result = await cc.distribute_task(task, ["nonexistent"])
        assert len(result) == 0


# ==================== distribute_filtered ====================


class TestDistributeFiltered:
    @pytest.mark.asyncio
    async def test_filter_fn(self):
        cc = ContextController()
        s1 = _make_session("s1")
        s2 = _make_session("s2")
        s1.session_id = "s1"
        s2.session_id = "s2"
        cc.register_session(s1)
        cc.register_session(s2)

        task = _make_task()
        result = await cc.distribute_filtered(
            task, filter_fn=lambda s: s.session_id == "s1"
        )
        assert result.success_count == 1
        assert "s1" in result.success

    @pytest.mark.asyncio
    async def test_filter_skips_inactive(self):
        cc = ContextController()
        s = _make_session("s1", active=False)
        cc.register_session(s)

        task = _make_task()
        result = await cc.distribute_filtered(task, filter_fn=lambda s: True)
        assert result.success_count == 0


# ==================== share_context ====================


class TestShareContext:
    @pytest.mark.asyncio
    async def test_share_between_sessions(self):
        cc = ContextController()
        msg = _make_msg_item(message_id="m1", role="assistant", content="hello")

        s1 = _make_session("s1")
        s1.memory.get_message_items.return_value = [msg]
        s1.memory.get_working_memory.return_value = []
        s2 = _make_session("s2")
        cc.register_session(s1)
        cc.register_session(s2)

        result = await cc.share_context("s1", ["s2"])
        assert result.get("s2", 0) >= 1

    @pytest.mark.asyncio
    async def test_share_skips_self(self):
        cc = ContextController()
        msg = _make_msg_item()
        s1 = _make_session("s1")
        s1.memory.get_message_items.return_value = [msg]
        s1.memory.get_working_memory.return_value = []
        cc.register_session(s1)

        result = await cc.share_context("s1", ["s1"])
        assert "s1" not in result

    @pytest.mark.asyncio
    async def test_share_source_missing(self):
        cc = ContextController()
        result = await cc.share_context("missing", ["s2"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_share_no_tasks(self):
        cc = ContextController()
        s1 = _make_session("s1")
        s2 = _make_session("s2")
        cc.register_session(s1)
        cc.register_session(s2)

        result = await cc.share_context("s1", ["s2"])
        assert result == {}


# ==================== get_shared_l3_context ====================


class TestGetSharedL3Context:
    def test_returns_relevant(self):
        cc = ContextController()
        cc.add_to_l3({"session_ids": ["s1", "s2"], "content": "shared"})
        cc.add_to_l3({"session_ids": ["s3"], "content": "other"})

        result = cc.get_shared_l3_context("s1")
        assert len(result) == 1
        assert result[0]["content"] == "shared"

    def test_global_summaries_included(self):
        cc = ContextController()
        cc.add_to_l3({"session_ids": [], "content": "global"})
        result = cc.get_shared_l3_context("any_session")
        assert len(result) == 1

    def test_limit(self):
        cc = ContextController()
        for i in range(10):
            cc.add_to_l3({"session_ids": ["s1"], "content": f"s{i}"})
        result = cc.get_shared_l3_context("s1", limit=3)
        assert len(result) == 3


# ==================== _allocate_budget ====================


class TestAllocateBudget:
    def test_equal_strategy(self):
        cc = ContextController()
        sessions = [_make_session(f"s{i}") for i in range(4)]
        budgets = cc._allocate_budget(sessions, 1000, "equal")
        assert budgets == [250, 250, 250, 250]

    def test_empty_sessions(self):
        cc = ContextController()
        assert cc._allocate_budget([], 1000, "equal") == []

    def test_default_strategy(self):
        cc = ContextController()
        sessions = [_make_session("s1")]
        budgets = cc._allocate_budget(sessions, 500, "unknown")
        assert budgets == [500]


# ==================== _estimate_tokens ====================


class TestEstimateTokens:
    def test_without_counter(self):
        cc = ContextController()
        result = cc._estimate_tokens("hello world")
        assert result == max(1, len("hello world") // 4)

    def test_with_counter(self):
        counter = MagicMock()
        counter.count.return_value = 42
        cc = ContextController(token_counter=counter)
        result = cc._estimate_tokens("test")
        assert result == 42
        counter.count.assert_called_once_with("test")

    def test_empty_string(self):
        cc = ContextController()
        assert cc._estimate_tokens("") == 1  # max(1, 0)


# ==================== aggregate_context ====================


class TestAggregateContext:
    @pytest.mark.asyncio
    async def test_empty_sessions(self):
        cc = ContextController()
        result = await cc.aggregate_context([], "query", 1000)
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_sessions(self):
        cc = ContextController()
        result = await cc.aggregate_context(["nonexistent"], "query", 1000)
        assert result == []

    @pytest.mark.asyncio
    async def test_with_l1_messages(self):
        cc = ContextController()
        msg = _make_msg_item(message_id="m1", role="assistant", content="relevant info")
        s = _make_session("s1")
        s.memory.get_message_items.return_value = [msg]
        cc.register_session(s)

        blocks = await cc.aggregate_context(["s1"], "query", 10000)
        assert len(blocks) >= 1
        assert blocks[0].source == "session:s1:L1"

    @pytest.mark.asyncio
    async def test_budget_respected(self):
        cc = ContextController()
        msgs = [_make_msg_item(message_id=f"m{i}", content="x" * 100, token_count=25) for i in range(10)]
        s = _make_session("s1")
        s.memory.get_message_items.return_value = msgs
        cc.register_session(s)

        # Very small budget
        blocks = await cc.aggregate_context(["s1"], "query", 50)
        total_tokens = sum(b.token_count for b in blocks)
        assert total_tokens <= 50
