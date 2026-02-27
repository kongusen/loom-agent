"""Tests for Blueprint Forge system: AgentBlueprint, BlueprintStore, BlueprintForge."""

import json
import pytest

from loom.cluster.blueprint_store import BlueprintStore
from loom.cluster.blueprint_forge import BlueprintForge
from loom.cluster import ClusterManager
from loom.cluster.amoeba_loop import AmoebaLoop
from loom.cluster.lifecycle import LifecycleManager
from loom.cluster.planner import TaskPlanner
from loom.cluster.reward import RewardBus
from loom.cluster.skill_registry import SkillNodeRegistry
from loom.config import ClusterConfig
from loom.types import (
    AgentNode,
    CapabilityProfile,
    TaskAd,
    TaskResult,
    TaskSpec,
)
from loom.types.blueprint import AgentBlueprint
from tests.conftest import MockLLMProvider


# ── AgentBlueprint dataclass ──


class TestAgentBlueprint:
    def test_defaults(self):
        bp = AgentBlueprint()
        assert len(bp.id) == 32  # uuid hex
        assert bp.name == ""
        assert bp.domain == "general"
        assert bp.generation == 1
        assert bp.parent_id is None
        assert bp.total_spawns == 0
        assert bp.reward_history == []

    def test_custom_values(self):
        bp = AgentBlueprint(
            name="coder",
            description="writes code",
            domain="code",
            domain_scores={"code": 0.9},
            generation=3,
            parent_id="abc",
        )
        assert bp.name == "coder"
        assert bp.domain == "code"
        assert bp.domain_scores == {"code": 0.9}
        assert bp.generation == 3
        assert bp.parent_id == "abc"


# ── BlueprintStore ──


class TestBlueprintStore:
    def test_save_and_get(self):
        store = BlueprintStore()
        bp = AgentBlueprint(name="test", domain="code")
        store.save(bp)
        assert store.get(bp.id) is bp
        assert store.count() == 1

    def test_get_missing(self):
        store = BlueprintStore()
        assert store.get("nonexistent") is None

    def test_list_all(self):
        store = BlueprintStore()
        bp1 = AgentBlueprint(name="a")
        bp2 = AgentBlueprint(name="b")
        store.save(bp1)
        store.save(bp2)
        assert len(store.list_all()) == 2

    def test_list_descriptions(self):
        store = BlueprintStore()
        store.save(AgentBlueprint(name="coder", description="writes code", domain="code"))
        descs = store.list_descriptions()
        assert len(descs) == 1
        assert descs[0]["name"] == "coder"
        assert descs[0]["description"] == "writes code"
        assert descs[0]["domain"] == "code"

    def test_find_by_domain(self):
        store = BlueprintStore()
        store.save(AgentBlueprint(name="a", domain="code"))
        store.save(AgentBlueprint(name="b", domain="math"))
        store.save(AgentBlueprint(name="c", domain="code"))
        assert len(store.find_by_domain("code")) == 2
        assert len(store.find_by_domain("math")) == 1
        assert len(store.find_by_domain("art")) == 0

    def test_prune_removes_low_reward(self):
        store = BlueprintStore()
        bad = AgentBlueprint(name="bad", total_tasks=5, avg_reward=0.1)
        good = AgentBlueprint(name="good", total_tasks=5, avg_reward=0.8)
        store.save(bad)
        store.save(good)
        pruned = store.prune(min_reward=0.2, min_tasks=3)
        assert bad.id in pruned
        assert store.get(bad.id) is None
        assert store.get(good.id) is good

    def test_prune_skips_low_task_count(self):
        store = BlueprintStore()
        bp = AgentBlueprint(name="new", total_tasks=1, avg_reward=0.05)
        store.save(bp)
        pruned = store.prune(min_reward=0.2, min_tasks=3)
        assert pruned == []
        assert store.count() == 1

    def test_persistence_roundtrip(self, tmp_path):
        path = tmp_path / "blueprints.json"
        store = BlueprintStore(persist_path=path)
        bp = AgentBlueprint(name="persist-me", domain="code", domain_scores={"code": 0.7})
        store.save(bp)
        assert path.exists()

        store2 = BlueprintStore(persist_path=path)
        loaded = store2.get(bp.id)
        assert loaded is not None
        assert loaded.name == "persist-me"
        assert loaded.domain_scores == {"code": 0.7}


# ── BlueprintForge ──


def _make_forge(llm=None):
    store = BlueprintStore()
    llm = llm or MockLLMProvider()
    return BlueprintForge(llm=llm, store=store), store


class TestBlueprintForge:
    @pytest.mark.asyncio
    async def test_forge_parses_llm_json(self):
        llm = MockLLMProvider([json.dumps({
            "name": "data-analyst",
            "description": "Analyzes datasets",
            "system_prompt": "You analyze data.",
            "domain": "data",
            "domain_scores": {"data": 0.8},
            "tools_filter": [],
        })])
        forge, store = _make_forge(llm)
        task = TaskAd(domain="data", description="Analyze CSV")
        bp = await forge.forge(task, context="user uploaded csv")
        assert bp.name == "data-analyst"
        assert bp.domain == "data"
        assert bp.domain_scores == {"data": 0.8}
        assert store.get(bp.id) is bp

    @pytest.mark.asyncio
    async def test_forge_fallback_on_bad_json(self):
        llm = MockLLMProvider(["not valid json at all"])
        forge, store = _make_forge(llm)
        task = TaskAd(domain="math", description="Solve equations")
        bp = await forge.forge(task)
        assert bp.name == "math-specialist"
        assert bp.domain == "math"
        assert store.count() == 1

    @pytest.mark.asyncio
    async def test_forge_fallback_on_exception(self):
        class FailLLM:
            async def complete(self, params):
                raise RuntimeError("LLM down")
        forge = BlueprintForge(llm=FailLLM(), store=BlueprintStore())
        task = TaskAd(domain="ops", description="Deploy service")
        bp = await forge.forge(task)
        assert bp.name == "ops-specialist"
        assert bp.domain == "ops"

    def test_spawn_creates_node(self):
        forge, store = _make_forge()
        bp = AgentBlueprint(
            name="coder", domain="code",
            system_prompt="You write code.",
            domain_scores={"code": 0.9},
            tools_filter=["search"],
        )
        store.save(bp)
        parent = AgentNode(id="parent-1", depth=0, capabilities=CapabilityProfile(tools=["shell"]))
        node = forge.spawn(bp, parent)
        assert node.id == f"forged:{bp.id[:8]}"
        assert node.blueprint_id == bp.id
        assert node.depth == 1
        assert node.capabilities.scores == {"code": 0.9}
        assert node.capabilities.tools == ["search"]
        assert bp.total_spawns == 1

    def test_spawn_inherits_parent_tools_when_no_filter(self):
        forge, store = _make_forge()
        bp = AgentBlueprint(name="gen", domain="general", system_prompt="Hi", tools_filter=[])
        store.save(bp)
        parent = AgentNode(id="p", depth=1, capabilities=CapabilityProfile(tools=["a", "b"]))
        node = forge.spawn(bp, parent)
        assert node.capabilities.tools == ["a", "b"]

    @pytest.mark.asyncio
    async def test_evolve_creates_next_generation(self):
        llm = MockLLMProvider([json.dumps({
            "description": "Better at data analysis",
            "system_prompt": "You are an improved data analyst.",
            "reasoning": "More focused prompt",
        })])
        forge, store = _make_forge(llm)
        parent_bp = AgentBlueprint(
            name="analyst", domain="data",
            description="Analyzes data", system_prompt="You analyze.",
            domain_scores={"data": 0.6}, generation=1,
            reward_history=[0.2, 0.3, 0.1],
        )
        store.save(parent_bp)
        new_bp = await forge.evolve(parent_bp)
        assert new_bp.generation == 2
        assert new_bp.parent_id == parent_bp.id
        assert new_bp.description == "Better at data analysis"
        assert new_bp.domain == "data"

    @pytest.mark.asyncio
    async def test_evolve_returns_original_on_failure(self):
        class FailLLM:
            async def complete(self, params):
                raise RuntimeError("down")
        forge = BlueprintForge(llm=FailLLM(), store=BlueprintStore())
        bp = AgentBlueprint(name="x", generation=2)
        result = await forge.evolve(bp)
        assert result is bp
        assert result.generation == 2

    @pytest.mark.asyncio
    async def test_match_returns_blueprint(self):
        bp = AgentBlueprint(name="coder", description="writes code", domain="code")
        llm = MockLLMProvider([json.dumps({"id": bp.id[:8]})])
        forge, store = _make_forge(llm)
        store.save(bp)
        task = TaskAd(domain="code", description="Write a parser")
        matched = await forge.match(task)
        assert matched is bp

    @pytest.mark.asyncio
    async def test_match_returns_none_when_empty(self):
        forge, _ = _make_forge()
        task = TaskAd(domain="code", description="anything")
        assert await forge.match(task) is None

    @pytest.mark.asyncio
    async def test_match_returns_none_on_no_match(self):
        llm = MockLLMProvider([json.dumps({"id": "none"})])
        forge, store = _make_forge(llm)
        store.save(AgentBlueprint(name="x"))
        task = TaskAd(domain="code", description="anything")
        assert await forge.match(task) is None


# ── Amoeba + Forge integration ──


def _make_amoeba_with_forge(llm=None):
    """Build AmoebaLoop with a BlueprintForge attached."""
    cm = ClusterManager()
    rb = RewardBus()
    lm = LifecycleManager(ClusterConfig(max_depth=3))
    llm = llm or MockLLMProvider()
    pl = TaskPlanner(llm)
    sr = SkillNodeRegistry()
    store = BlueprintStore()
    forge = BlueprintForge(llm=llm, store=store)
    loop = AmoebaLoop(
        cluster=cm, reward_bus=rb, lifecycle=lm,
        planner=pl, skill_registry=sr, llm=llm, forge=forge,
    )
    return loop, cm, forge, store


class TestAmoebaForgeIntegration:
    @pytest.mark.asyncio
    async def test_sense_and_match_forge_fallback(self):
        """When no skill/node matches, forge creates a blueprint and spawns."""
        # LLM call 1: sense_and_match routing → no skill match
        # LLM call 2: forge.match → no existing blueprint
        # LLM call 3: forge.forge → creates new blueprint
        llm = MockLLMProvider([
            json.dumps({"skill": "nonexistent", "complexity": 0.5, "domains": ["code"]}),
            json.dumps({"id": "none"}),
            json.dumps({
                "name": "code-writer",
                "description": "Writes code",
                "system_prompt": "You write code.",
                "domain": "code",
                "domain_scores": {"code": 0.8},
                "tools_filter": [],
            }),
        ])
        loop, cm, forge, store = _make_amoeba_with_forge(llm)
        # Add a busy parent so find_idle() returns None but fallback_parent exists
        parent = AgentNode(id="root", depth=0, status="busy", capabilities=CapabilityProfile())
        cm.add_node(parent)

        spec, winner = await loop._sense_and_match("Write a Python parser")
        assert winner is not None
        assert winner.blueprint_id is not None
        assert store.count() == 1

    @pytest.mark.asyncio
    async def test_evaluate_propagates_reward_to_blueprint(self):
        """Reward from task execution flows back to the blueprint."""
        llm = MockLLMProvider()
        loop, cm, forge, store = _make_amoeba_with_forge(llm)
        bp = AgentBlueprint(name="test-bp", domain="code")
        store.save(bp)
        node = AgentNode(
            id="forged:test", blueprint_id=bp.id, depth=1,
            capabilities=CapabilityProfile(scores={"code": 0.7}),
        )
        cm.add_node(node)
        spec = TaskSpec(
            task=TaskAd(domain="code", description="test", estimated_complexity=0.5),
            objective="test",
        )
        result = TaskResult(
            task_id=spec.task.task_id, agent_id=node.id,
            content="done", success=True, token_cost=100, duration_ms=500,
        )
        reward, recycled = await loop._evaluate_and_adapt(node, spec, result)
        assert reward > 0
        assert bp.total_tasks == 1
        assert len(bp.reward_history) == 1
        assert bp.reward_history[0] == reward
