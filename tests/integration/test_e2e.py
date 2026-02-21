"""Integration tests — end-to-end flows."""

import pytest
from loom.agent import Agent
from loom.runtime.core import Runtime
from loom.types import (
    AgentNode, TaskAd, CapabilityProfile, DoneEvent,
    Document, Skill, SkillTrigger,
)
from loom.config import AgentConfig
from loom.knowledge.base import KnowledgeBase
from tests.conftest import MockLLMProvider, MockEmbeddingProvider


class TestAgentEndToEnd:
    async def test_agent_run_full_cycle(self):
        """Agent: input → memory → context → LLM → done event."""
        agent = Agent(
            provider=MockLLMProvider(["The answer is 42"]),
            config=AgentConfig(max_steps=1, stream=False),
        )
        result = await agent.run("What is the answer?")
        assert isinstance(result, DoneEvent)
        assert "42" in result.content
        assert len(agent.memory.get_history()) >= 1

    async def test_agent_event_propagation(self):
        """Events emitted during agent run reach registered handlers."""
        agent = Agent(
            provider=MockLLMProvider(["hello"]),
            config=AgentConfig(max_steps=1, stream=False),
        )
        events = []
        agent.on("done", lambda e: events.append(e))
        await agent.run("hi")
        assert len(events) >= 1


class TestRuntimeEndToEnd:
    async def test_runtime_submit_task(self):
        """Runtime: add agent → submit task → get result."""
        rt = Runtime(MockLLMProvider(["task completed"]))
        rt.add_agent(capabilities=CapabilityProfile(scores={"code": 0.8}))
        result = await rt.submit(TaskAd(domain="code", description="write code"))
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_runtime_reward_updates(self):
        """Runtime: task execution updates reward history."""
        rt = Runtime(MockLLMProvider(["done"]))
        node = rt.add_agent(capabilities=CapabilityProfile(scores={"code": 0.8}))
        await rt.submit(TaskAd(domain="code", description="test"))
        assert len(node.reward_history) >= 1


class TestKnowledgePipeline:
    async def test_ingest_and_query(self):
        """Knowledge: ingest docs → query → get results."""
        kb = KnowledgeBase()
        await kb.ingest([Document(id="d1", content="Python is a programming language")])
        results = await kb.query("Python")
        assert len(results) >= 1
        assert "Python" in results[0].chunk.content
