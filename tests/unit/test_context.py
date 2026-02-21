"""Unit tests for context module."""

import pytest
from loom.types import ContextFragment
from loom.context import ContextOrchestrator


class _StubProvider:
    def __init__(self, source, frags):
        self.source = source
        self._frags = frags

    async def provide(self, query, budget):
        return self._frags


class TestContextOrchestrator:
    async def test_empty(self):
        orch = ContextOrchestrator()
        assert await orch.gather("q", 1000) == []

    async def test_gather_single_provider(self):
        orch = ContextOrchestrator()
        frags = [ContextFragment(source="memory", content="data", tokens=10, relevance=0.8)]
        orch.register(_StubProvider("memory", frags))
        result = await orch.gather("q", 1000)
        assert len(result) == 1

    async def test_budget_enforcement(self):
        orch = ContextOrchestrator()
        frags = [
            ContextFragment(source="memory", content="a", tokens=600, relevance=0.9),
            ContextFragment(source="memory", content="b", tokens=600, relevance=0.5),
        ]
        orch.register(_StubProvider("memory", frags))
        result = await orch.gather("q", 1000)
        assert len(result) == 1

    async def test_multi_provider_merge(self):
        orch = ContextOrchestrator()
        orch.register(_StubProvider("memory", [
            ContextFragment(source="memory", content="m", tokens=10, relevance=0.7),
        ]))
        orch.register(_StubProvider("knowledge", [
            ContextFragment(source="knowledge", content="k", tokens=10, relevance=0.9),
        ]))
        result = await orch.gather("q", 1000)
        assert len(result) == 2
        assert result[0].source == "knowledge"  # higher relevance first

    def test_compute_budget(self):
        orch = ContextOrchestrator(context_window=100000, output_reserve_ratio=0.25)
        b = orch.compute_budget("system prompt")
        assert b.available > 0
        assert b.reserved_output == 25000
