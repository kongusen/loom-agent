"""Coverage-boost tests for cluster: amoeba_loop, orchestrate, cluster_provider, skill_registry."""

import pytest

from loom.cluster import ClusterManager
from loom.cluster.amoeba_loop import AmoebaLoop
from loom.cluster.cluster_provider import ClusterProvider
from loom.cluster.lifecycle import LifecycleManager
from loom.cluster.planner import TaskPlanner
from loom.cluster.reward import RewardBus
from loom.cluster.skill_registry import SkillNodeRegistry
from loom.config import ClusterConfig
from loom.types import (
    AgentNode,
    CapabilityProfile,
    ComplexityEstimate,
    RewardRecord,
    Skill,
    TaskAd,
    TaskResult,
    TaskSpec,
)
from tests.conftest import MockLLMProvider


def _make_amoeba(llm=None):
    cm = ClusterManager()
    rb = RewardBus()
    lm = LifecycleManager(ClusterConfig(max_depth=3))
    llm = llm or MockLLMProvider()
    pl = TaskPlanner(llm)
    sr = SkillNodeRegistry()
    return AmoebaLoop(
        cluster=cm, reward_bus=rb, lifecycle=lm, planner=pl, skill_registry=sr, llm=llm
    )


class TestAmoebaHelpers:
    def test_collect_skill_descriptions_empty(self):
        a = _make_amoeba()
        assert a._collect_skill_descriptions() == []

    def test_collect_skill_descriptions_with_skills(self):
        a = _make_amoeba()
        a._skills.register(Skill(name="coder", description="writes code"))
        a._skills.register(Skill(name="writer", description="writes docs"))
        descs = a._collect_skill_descriptions()
        assert len(descs) == 2
        assert any(d["name"] == "coder" for d in descs)

    def test_build_enriched_prompt(self):
        a = _make_amoeba()
        spec = TaskSpec(
            task=TaskAd(domain="general", description="test", estimated_complexity=0.5),
            objective="Build app",
            output_format="JSON",
            boundaries="No external APIs",
        )
        result = a._build_enriched_prompt(spec)
        assert "Build app" in result
        assert "JSON" in result
        assert "No external APIs" in result

    def test_derive_actual_complexity(self):
        a = _make_amoeba()
        r = TaskResult(
            task_id="t",
            agent_id="a",
            content="ok",
            success=True,
            token_cost=4096,
            duration_ms=15000,
        )
        c = a._derive_actual_complexity(r)
        assert 0 < c < 1.0

    def test_record_and_calibrate(self):
        a = _make_amoeba()
        for _ in range(5):
            a._record_calibration("code", 0.3, 0.6)
        est = ComplexityEstimate(score=0.3, domains=["code"], method="heuristic")
        cal = a._calibrate(est)
        assert cal.score != est.score  # bias applied

    def test_calibrate_no_data(self):
        a = _make_amoeba()
        est = ComplexityEstimate(score=0.5, domains=["code"], method="heuristic")
        assert a._calibrate(est).score == 0.5

    def test_should_evolve_skill_not_enough_history(self):
        a = _make_amoeba()
        node = AgentNode(id="n")
        assert a._should_evolve_skill(node) is False

    def test_should_evolve_skill_low_reward(self):
        a = _make_amoeba()
        node = AgentNode(
            id="n", reward_history=[RewardRecord(reward=0.1, domain="code") for _ in range(5)]
        )
        assert a._should_evolve_skill(node) is True


class TestAmoebaAsync:
    async def test_llm_sense_and_match(self):
        llm = MockLLMProvider(['{"skill":"coder","complexity":0.7,"domains":["code"]}'])
        a = _make_amoeba(llm)
        skills = [{"name": "coder", "description": "writes code"}]
        complexity, selected, domains = await a._llm_sense_and_match("build app", skills)
        assert complexity == pytest.approx(0.7)
        assert selected == "coder"
        assert "code" in domains

    async def test_llm_sense_and_match_fallback(self):
        llm = MockLLMProvider(["not json"])
        a = _make_amoeba(llm)
        skills = [{"name": "coder", "description": "writes code"}]
        complexity, selected, domains = await a._llm_sense_and_match("task", skills)
        assert complexity == 0.5
        assert selected == "coder"  # falls back to first skill

    async def test_sense_and_match(self):
        llm = MockLLMProvider(['{"skill":"coder","complexity":0.6,"domains":["code"]}'])
        a = _make_amoeba(llm)
        a._skills.register(Skill(name="coder", description="writes code"))
        spec, winner = await a._sense_and_match("write a function")
        assert spec.task is not None
        assert spec.objective == "write a function"
        assert winner is not None

    async def test_resolve_skill_node(self):
        a = _make_amoeba()
        a._skills.register(Skill(name="coder", description="writes code"))
        node = a._resolve_skill_node("coder")
        assert node is not None
        assert node.id == "skill:coder"
        assert len(a._cluster.nodes) == 1

    async def test_trigger_skill_evolution(self):
        llm = MockLLMProvider(
            ['{"domain": "code", "boost": 0.2, "reasoning": "needs improvement"}']
        )
        a = _make_amoeba(llm)
        node = AgentNode(id="n", capabilities=CapabilityProfile(scores={"code": 0.5}))
        spec = TaskSpec(task=TaskAd(domain="code"), objective="test")
        await a._trigger_skill_evolution(node, spec)
        assert node.capabilities.scores["code"] == pytest.approx(0.7)


class TestSkillNodeRegistry:
    def test_register_and_get(self):
        sr = SkillNodeRegistry()
        s = Skill(name="code")
        sr.register(s)
        assert sr.get("code") is s
        assert sr.size == 1

    def test_register_all(self):
        sr = SkillNodeRegistry()
        sr.register_all([Skill(name="a"), Skill(name="b")])
        assert sr.size == 2

    def test_mark_loaded(self):
        sr = SkillNodeRegistry()
        sr.register(Skill(name="x"))
        sr.mark_loaded("x")
        assert sr.is_loaded("x")

    async def test_find_match_keyword(self):
        sr = SkillNodeRegistry()
        sr.register(
            Skill(name="py", trigger={"type": "keyword", "keywords": ["python"]}, priority=0.8)
        )
        result = await sr.find_match("python help")
        assert result is not None
        assert result["skill"].name == "py"

    async def test_find_match_skips_loaded(self):
        sr = SkillNodeRegistry()
        sr.register(
            Skill(name="py", trigger={"type": "keyword", "keywords": ["python"]}, priority=0.8)
        )
        sr.mark_loaded("py")
        result = await sr.find_match("python help")
        assert result is None

    async def test_find_match_no_trigger(self):
        sr = SkillNodeRegistry()
        sr.register(Skill(name="plain"))
        result = await sr.find_match("anything")
        assert result is None


class TestClusterProvider:
    async def test_provide_with_node(self):
        cm = ClusterManager()
        node = AgentNode(id="a1", capabilities=CapabilityProfile(scores={"code": 0.9}))
        cm.add_node(node)
        cp = ClusterProvider(cm, "a1")
        frags = await cp.provide("query", budget=1000)
        assert len(frags) >= 1
        assert "code" in frags[0].content

    async def test_provide_no_node(self):
        cm = ClusterManager()
        cp = ClusterProvider(cm, "missing")
        frags = await cp.provide("query", budget=1000)
        assert frags == []

    async def test_provide_with_peers(self):
        cm = ClusterManager()
        cm.add_node(AgentNode(id="a1", capabilities=CapabilityProfile(scores={"code": 0.9})))
        cm.add_node(AgentNode(id="a2", capabilities=CapabilityProfile(scores={"data": 0.8})))
        cp = ClusterProvider(cm, "a1")
        frags = await cp.provide("query", budget=5000)
        assert len(frags) == 2  # caps + peers
