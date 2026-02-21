"""Coverage-boost tests for memory module: summarizer, tokens, provider, manager extended."""

import pytest
from loom.memory.tokens import _estimate_tokens, _msg_tokens, EstimatorTokenizer
from loom.memory.summarizer import LLMSummarizer
from loom.memory.provider import MemoryProvider
from loom.memory import MemoryManager
from loom.types import MemoryEntry, UserMessage, AssistantMessage, ToolCall, ContextFragment
from tests.conftest import MockLLMProvider


class TestEstimatorTokenizer:
    def test_count(self):
        t = EstimatorTokenizer()
        assert t.count("hello world") > 0

    def test_truncate_short(self):
        t = EstimatorTokenizer()
        assert t.truncate("hi", 100) == "hi"

    def test_truncate_long(self):
        t = EstimatorTokenizer(chars_per_token=4)
        result = t.truncate("a" * 100, 5)
        assert len(result) == 20


class TestTokenHelpers:
    def test_estimate_tokens(self):
        assert _estimate_tokens("hello") >= 1

    def test_msg_tokens_user(self):
        assert _msg_tokens(UserMessage(content="hello")) >= 1

    def test_msg_tokens_assistant_with_tool_calls(self):
        msg = AssistantMessage(content="ok", tool_calls=[ToolCall(id="t1", name="search", arguments='{"q":"x"}')])
        tokens = _msg_tokens(msg)
        assert tokens > _msg_tokens(AssistantMessage(content="ok"))


class TestLLMSummarizer:
    async def test_compress(self):
        llm = MockLLMProvider(["Summary of conversation"])
        tok = EstimatorTokenizer()
        s = LLMSummarizer(llm, tok)
        entries = [
            MemoryEntry(content="User asked about Python", tokens=10, importance=0.5),
            MemoryEntry(content="Agent explained Python", tokens=10, importance=0.7),
        ]
        result = await s.compress(entries)
        assert result.content == "Summary of conversation"
        assert result.importance == pytest.approx(0.8)  # max(0.7) + 0.1
        assert result.metadata["compressed"] is True
        assert result.metadata["source_count"] == 2


class TestMemoryProvider:
    async def test_provide_returns_fragments(self):
        mgr = MemoryManager()
        await mgr.l2.store(MemoryEntry(content="test data", tokens=5, importance=0.8, metadata={"role": "user"}))
        tok = EstimatorTokenizer()
        provider = MemoryProvider(mgr, tok)
        frags = await provider.provide("test", budget=1000)
        assert len(frags) >= 1
        assert isinstance(frags[0], ContextFragment)
        assert frags[0].source == "memory"


class TestMemoryManagerExtended:
    async def test_build_context(self):
        mgr = MemoryManager()
        mgr.l1.add(UserMessage(content="hello"))
        result = await mgr.build_context("hello", budget=1000)
        assert "hello" in result

    async def test_build_context_with_l2(self):
        mgr = MemoryManager()
        await mgr.l2.store(MemoryEntry(content="stored fact", tokens=5, importance=0.8))
        result = await mgr.build_context("fact", budget=1000)
        assert "stored fact" in result

    async def test_persist(self):
        mgr = MemoryManager()
        entries = [MemoryEntry(content="persist me", tokens=5, importance=0.5)]
        await mgr.persist(entries)
        l3 = await mgr.get_l3_context("persist")
        assert len(l3) >= 1

    async def test_absorb(self):
        mgr = MemoryManager()
        entries = [MemoryEntry(content="absorbed", tokens=5, importance=0.3)]
        await mgr.absorb(entries, boost=0.2)
        l2 = await mgr.get_l2_context("absorbed")
        assert len(l2) >= 1
        assert l2[0].importance == pytest.approx(0.5)
