"""Coverage-boost tests for knowledge/provider.py."""

import pytest
from loom.knowledge.provider import KnowledgeProvider
from loom.knowledge.base import KnowledgeBase
from loom.types import Document, ContextFragment


class TestKnowledgeProvider:
    async def test_provide(self):
        kb = KnowledgeBase()
        await kb.ingest([Document(id="d1", content="Python is great")])
        p = KnowledgeProvider(kb)
        frags = await p.provide("Python", budget=1000)
        assert len(frags) >= 1
        assert isinstance(frags[0], ContextFragment)
        assert frags[0].source == "knowledge"

    async def test_budget_limit(self):
        kb = KnowledgeBase()
        await kb.ingest([Document(id="d1", content="x" * 200)])
        p = KnowledgeProvider(kb)
        frags = await p.provide("x", budget=2)
        assert len(frags) == 0
