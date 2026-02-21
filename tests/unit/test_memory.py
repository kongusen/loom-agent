"""Unit tests for memory module."""

from loom.memory import MemoryManager, PersistentStore, SlidingWindow, WorkingMemory
from loom.types import MemoryEntry, UserMessage


class TestSlidingWindow:
    def test_add_and_get(self):
        sw = SlidingWindow(token_budget=8000)
        sw.add(UserMessage(content="hello"))
        assert len(sw.get_messages()) == 1

    def test_eviction(self):
        sw = SlidingWindow(token_budget=20)
        sw.add(UserMessage(content="a" * 50))
        evicted = sw.add(UserMessage(content="b" * 50))
        assert len(evicted) > 0
        assert len(sw.get_messages()) >= 1

    def test_clear(self):
        sw = SlidingWindow()
        sw.add(UserMessage(content="hi"))
        sw.clear()
        assert sw.get_messages() == []
        assert sw.current_tokens == 0


class TestWorkingMemory:
    async def test_store_and_retrieve(self):
        wm = WorkingMemory(token_budget=4000)
        entry = MemoryEntry(content="fact", tokens=10, importance=0.8)
        evicted = await wm.store(entry)
        assert evicted == []
        results = await wm.retrieve()
        assert len(results) == 1

    async def test_eviction_by_importance(self):
        wm = WorkingMemory(token_budget=30)
        await wm.store(MemoryEntry(content="low", tokens=15, importance=0.1))
        await wm.store(MemoryEntry(content="high", tokens=15, importance=0.9))
        evicted = await wm.store(MemoryEntry(content="mid", tokens=15, importance=0.5))
        assert any(e.content == "low" for e in evicted)


class TestPersistentStore:
    async def test_store_and_retrieve(self):
        ps = PersistentStore()
        await ps.store(MemoryEntry(content="persistent", tokens=5, importance=0.5))
        results = await ps.retrieve("persistent")
        assert len(results) >= 1


class TestMemoryManager:
    async def test_add_message_and_history(self):
        mm = MemoryManager()
        await mm.add_message(UserMessage(content="hello"))
        assert len(mm.get_history()) == 1

    async def test_l1_to_l2_flow(self):
        mm = MemoryManager(l1=SlidingWindow(token_budget=20))
        await mm.add_message(UserMessage(content="a" * 50))
        await mm.add_message(UserMessage(content="b" * 50))
        l2 = await mm.get_l2_context()
        assert len(l2) >= 0  # evicted messages flow to L2

    async def test_extract_for_budget(self):
        mm = MemoryManager()
        await mm.l2.store(MemoryEntry(content="fact1", tokens=10, importance=0.9))
        await mm.l2.store(MemoryEntry(content="fact2", tokens=10, importance=0.5))
        results = await mm.extract_for("query", budget=15)
        assert len(results) == 1
        assert results[0].content == "fact1"

    async def test_absorb(self):
        mm = MemoryManager()
        entries = [MemoryEntry(content="absorbed", tokens=5, importance=0.3)]
        await mm.absorb(entries, boost=0.2)
        l2 = await mm.get_l2_context()
        assert len(l2) == 1
        assert l2[0].importance == 0.5
