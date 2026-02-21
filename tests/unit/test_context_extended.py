"""Coverage-boost tests for context providers: MitosisContextProvider, MemoryContextProvider."""

from loom.context.memory_provider import MemoryContextProvider
from loom.context.mitosis_provider import MitosisContextProvider
from loom.memory import MemoryManager
from loom.types import ContextSource, MemoryEntry, MitosisContext, SubTask, TaskAd, TaskSpec


def _dummy_task(**kw):
    defaults = {"domain": "general", "description": "test", "estimated_complexity": 0.5}
    defaults.update(kw)
    return TaskAd(**defaults)


class TestMitosisContextProvider:
    async def test_full_context(self):
        ctx = MitosisContext(
            parent_task_spec=TaskSpec(task=_dummy_task(), objective="Build an app"),
            subtask=SubTask(id="s1", description="Write tests"),
            parent_tools=["search", "shell"],
        )
        p = MitosisContextProvider(ctx)
        frags = await p.provide("query", budget=5000)
        assert len(frags) == 1
        assert "Build an app" in frags[0].content
        assert "Write tests" in frags[0].content
        assert "search" in frags[0].content
        assert frags[0].source == ContextSource.MITOSIS

    async def test_empty_context(self):
        ctx = MitosisContext()
        p = MitosisContextProvider(ctx)
        frags = await p.provide("query", budget=5000)
        assert frags == []

    async def test_partial_context(self):
        ctx = MitosisContext(parent_task_spec=TaskSpec(task=_dummy_task(), objective="Goal"))
        p = MitosisContextProvider(ctx)
        frags = await p.provide("query", budget=5000)
        assert len(frags) == 1
        assert "Goal" in frags[0].content

    async def test_budget_truncation(self):
        ctx = MitosisContext(
            parent_task_spec=TaskSpec(task=_dummy_task(), objective="x" * 500),
            subtask=SubTask(id="s1", description="y" * 500),
            parent_tools=["a", "b", "c"],
        )
        p = MitosisContextProvider(ctx)
        frags = await p.provide("query", budget=5)
        assert len(frags) == 1
        assert frags[0].tokens == 5


class TestMemoryContextProvider:
    async def test_provide_from_l2(self):
        mgr = MemoryManager()
        await mgr.l2.store(MemoryEntry(content="important fact", tokens=5, importance=0.9))
        p = MemoryContextProvider(mgr)
        frags = await p.provide("fact", budget=1000)
        assert len(frags) >= 1
        assert frags[0].source == ContextSource.MEMORY

    async def test_budget_limit(self):
        mgr = MemoryManager()
        await mgr.l2.store(MemoryEntry(content="big entry", tokens=100, importance=0.9))
        p = MemoryContextProvider(mgr)
        frags = await p.provide("big", budget=10)
        assert len(frags) == 0

    async def test_sorted_by_importance(self):
        mgr = MemoryManager()
        await mgr.l2.store(MemoryEntry(content="low", tokens=5, importance=0.2))
        await mgr.l2.store(MemoryEntry(content="high", tokens=5, importance=0.9))
        p = MemoryContextProvider(mgr)
        frags = await p.provide("query", budget=1000)
        if len(frags) >= 2:
            assert frags[0].relevance >= frags[1].relevance
