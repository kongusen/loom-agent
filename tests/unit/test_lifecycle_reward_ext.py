"""Coverage-boost tests for lifecycle mitosis, reward decay, skills provider extended."""

import time

import pytest

from loom.cluster.lifecycle import LifecycleManager
from loom.cluster.reward import RewardBus
from loom.config import ClusterConfig
from loom.errors import MitosisError
from loom.skills.provider import SkillProvider
from loom.skills.registry import SkillRegistry
from loom.types import (
    AgentNode,
    CapabilityProfile,
    ContextFragment,
    RewardRecord,
    SkillTrigger,
    TaskAd,
)
from tests.conftest import MockLLMProvider


class TestLifecycleMitosis:
    def test_mitosis_creates_child(self):
        lm = LifecycleManager(ClusterConfig(max_depth=3))
        parent = AgentNode(id="p", depth=1, capabilities=CapabilityProfile(tools=["search"]))
        task = TaskAd(domain="code", description="test")
        from loom.agent import Agent

        child = lm.mitosis(parent, task, lambda depth: Agent(provider=MockLLMProvider()))
        assert child.depth == 2
        assert "search" in child.capabilities.tools

    def test_mitosis_max_depth_error(self):
        lm = LifecycleManager(ClusterConfig(max_depth=2))
        parent = AgentNode(id="p", depth=2)
        with pytest.raises(MitosisError):
            lm.mitosis(parent, TaskAd(domain="code"), lambda d: None)

    def test_find_merge_target(self):
        lm = LifecycleManager()
        dying = AgentNode(id="d", capabilities=CapabilityProfile(scores={"code": 0.9}))
        c1 = AgentNode(id="c1", capabilities=CapabilityProfile(scores={"data": 0.8}))
        c2 = AgentNode(id="c2", capabilities=CapabilityProfile(scores={"code": 0.85}))
        target = lm.find_merge_target(dying, [c1, c2])
        assert target is not None

    def test_check_health_warning(self):
        lm = LifecycleManager(ClusterConfig(consecutive_loss_limit=6))
        node = AgentNode(
            id="w",
            consecutive_losses=3,
            last_active_at=time.time(),
            reward_history=[RewardRecord(reward=0.8, domain="code")],
        )
        report = lm.check_health(node)
        assert report.status == "warning"

    def test_check_health_dying_no_history(self):
        lm = LifecycleManager()
        node = AgentNode(id="d", last_active_at=0)
        report = lm.check_health(node)
        assert report.status == "dying"
        assert report.recommendation == "recycle"


class TestRewardBusExtended:
    def test_decay_inactive(self):
        rb = RewardBus()
        node = AgentNode(
            id="n",
            capabilities=CapabilityProfile(scores={"code": 0.9}),
            reward_history=[RewardRecord(reward=0.5, domain="code")],
        )
        rb.decay_inactive(node)
        assert node.capabilities.scores["code"] <= 0.9

    def test_set_llm_judge(self):
        rb = RewardBus()
        rb.set_llm_judge(lambda n, t, s: 0.8, interval=3)
        assert rb._llm_judge is not None
        assert rb._judge_interval == 3

    async def test_evaluate_hybrid_no_judge(self):
        rb = RewardBus()
        node = AgentNode(id="n", capabilities=CapabilityProfile(scores={"code": 0.5}))
        task = TaskAd(domain="code", description="test")
        r = await rb.evaluate_hybrid(node, task, True, token_cost=100)
        assert r > 0

    async def test_evaluate_hybrid_with_judge(self):
        rb = RewardBus()

        async def _judge(n, t, s):
            return 0.9

        rb.set_llm_judge(_judge, interval=1)
        node = AgentNode(id="n", capabilities=CapabilityProfile(scores={"code": 0.5}))
        task = TaskAd(domain="code", description="test")
        r = await rb.evaluate_hybrid(node, task, True, token_cost=100)
        assert r > 0


class TestSkillProviderExtended:
    async def test_provide_with_custom_context(self):
        reg = SkillRegistry()

        class CustomSkill:
            name = "custom"
            trigger = SkillTrigger(type="keyword", keywords=["test"])
            priority = 0.8
            activation_level = "auto"

            async def provide_context(self, query, budget):
                return [
                    ContextFragment(source="skill", content="custom ctx", tokens=5, relevance=0.9)
                ]

        reg.register(CustomSkill())
        p = SkillProvider(reg)
        frags = await p.provide("test query", budget=1000)
        assert any("custom ctx" in f.content for f in frags)
