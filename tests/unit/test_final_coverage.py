"""Final coverage-boost tests: orchestrate, schema, registry activate/deactivate, KB delete, activator patterns."""

from pydantic import BaseModel

from loom.cluster import ClusterManager
from loom.cluster.lifecycle import LifecycleManager
from loom.cluster.orchestrate import OrchestrateStrategy
from loom.cluster.planner import TaskPlanner
from loom.cluster.reward import RewardBus
from loom.knowledge.base import KnowledgeBase
from loom.skills.activator import _evaluate
from loom.skills.registry import SkillRegistry
from loom.tools.schema import DictSchema, PydanticSchema
from loom.types import (
    AgentNode,
    CapabilityProfile,
    Document,
    DoneEvent,
    ErrorEvent,
    SkillTrigger,
    TextDeltaEvent,
    UserMessage,
)
from tests.conftest import (
    MockEmbeddingProvider,
    MockEntityExtractor,
    MockGraphStore,
    MockLLMProvider,
)

# ── Schema tests ──


class TestPydanticSchema:
    def test_parse_dict(self):
        class M(BaseModel):
            x: int

        s = PydanticSchema(M)
        r = s.parse({"x": 42})
        assert r.x == 42

    def test_parse_json_string(self):
        class M(BaseModel):
            x: int

        s = PydanticSchema(M)
        r = s.parse('{"x": 7}')
        assert r.x == 7

    def test_to_json_schema(self):
        class M(BaseModel):
            x: int

        s = PydanticSchema(M)
        js = s.to_json_schema()
        assert "properties" in js


class TestDictSchema:
    def test_parse_dict(self):
        s = DictSchema({"type": "object"})
        assert s.parse({"a": 1}) == {"a": 1}

    def test_parse_non_dict(self):
        s = DictSchema({"type": "object"})
        assert s.parse("not a dict") == {}

    def test_to_json_schema(self):
        schema = {"type": "object", "properties": {}}
        s = DictSchema(schema)
        assert s.to_json_schema() is schema


# ── Activator pattern + match_all tests ──


class TestActivatorPatterns:
    def test_pattern_trigger_match(self):
        trigger = SkillTrigger(type="pattern", pattern=r"\bdef\b")
        result = _evaluate(trigger, "def foo():")
        assert result is not None
        assert result[0] == 1.0

    def test_pattern_trigger_no_match(self):
        trigger = SkillTrigger(type="pattern", pattern=r"\bclass\b")
        result = _evaluate(trigger, "def foo():")
        assert result is None

    def test_keyword_match_all_pass(self):
        trigger = SkillTrigger(type="keyword", keywords=["python", "code"], match_all=True)
        result = _evaluate(trigger, "python code review")
        assert result is not None

    def test_keyword_match_all_fail(self):
        trigger = SkillTrigger(type="keyword", keywords=["python", "rust"], match_all=True)
        result = _evaluate(trigger, "python code review")
        assert result is None

    def test_unknown_trigger_type(self):
        trigger = SkillTrigger(type="unknown")
        result = _evaluate(trigger, "anything")
        assert result is None


# ── SkillRegistry activate/deactivate ──


class TestSkillRegistryActivate:
    async def test_activate_auto_with_on_activate(self):
        reg = SkillRegistry()
        activated = []

        class S:
            name = "s1"
            trigger = SkillTrigger(type="keyword", keywords=["test"])
            priority = 0.5
            activation_level = "auto"

            async def on_activate(self):
                activated.append(True)

        reg.register(S())
        results = await reg.activate("test input")
        assert len(results) == 1
        assert activated == [True]

    async def test_activate_on_demand_skipped(self):
        reg = SkillRegistry()

        class S:
            name = "od"
            trigger = SkillTrigger(type="keyword", keywords=["test"])
            priority = 0.5
            activation_level = "on-demand"

        reg.register(S())
        results = await reg.activate("test input")
        assert len(results) == 0

    async def test_activate_always(self):
        reg = SkillRegistry()

        class S:
            name = "alw"
            activation_level = "always"
            trigger = None
            priority = 1.0

        reg.register(S())
        results = await reg.activate("anything")
        assert len(results) == 1
        assert results[0].reason == "always active"

    async def test_deactivate_with_callback(self):
        reg = SkillRegistry()
        deactivated = []

        class S:
            name = "d1"
            activation_level = "always"
            trigger = None
            priority = 1.0

            async def on_deactivate(self):
                deactivated.append(True)

        reg.register(S())
        assert "d1" in reg._active
        await reg.deactivate("d1")
        assert "d1" not in reg._active
        assert deactivated == [True]

    async def test_deactivate_missing(self):
        reg = SkillRegistry()
        await reg.deactivate("nonexistent")  # no error

    def test_get_active(self):
        reg = SkillRegistry()

        class S:
            name = "a1"
            activation_level = "always"

        reg.register(S())
        assert len(reg.get_active()) == 1

    def test_all(self):
        reg = SkillRegistry()

        class S:
            name = "x"
            activation_level = "auto"

        reg.register(S())
        assert len(reg.all()) == 1


# ── OrchestrateStrategy ──


class TestOrchestrateStrategy:
    async def test_no_winner(self):
        cm = ClusterManager()
        rb = RewardBus()
        lm = LifecycleManager()
        pl = TaskPlanner(MockLLMProvider())
        strat = OrchestrateStrategy(cm, rb, lm, pl)

        class FakeCtx:
            messages = [UserMessage(content="hello")]

        events = [e async for e in strat.execute(FakeCtx())]
        types = [type(e) for e in events]
        assert ErrorEvent in types
        assert DoneEvent in types

    async def test_with_winner(self):
        cm = ClusterManager()
        rb = RewardBus()
        lm = LifecycleManager()
        pl = TaskPlanner(MockLLMProvider())
        strat = OrchestrateStrategy(cm, rb, lm, pl)

        from loom.agent import Agent

        agent = Agent(provider=MockLLMProvider(["orchestrated result"]))
        node = AgentNode(id="w1", capabilities=CapabilityProfile(scores={"general": 0.9}))
        node.agent = agent
        cm.add_node(node)

        class FakeCtx:
            messages = [UserMessage(content="hello")]

        events = [e async for e in strat.execute(FakeCtx())]
        texts = [e.text for e in events if isinstance(e, TextDeltaEvent)]
        assert any("orchestrated result" in t for t in texts)
        assert node.status == "idle"


# ── KnowledgeBase delete + graph ingest ──


class TestKnowledgeBaseExtended:
    async def test_delete_document(self):
        kb = KnowledgeBase()
        await kb.ingest([Document(id="d1", content="hello world")])
        results = await kb.query("hello")
        assert len(results) > 0
        await kb.delete(["d1"])
        results = await kb.query("hello")
        assert len(results) == 0

    async def test_ingest_with_graph(self):
        gs = MockGraphStore()
        ee = MockEntityExtractor()
        kb = KnowledgeBase(graph_store=gs, entity_extractor=ee)
        await kb.ingest([Document(id="d1", content="Python is great")])
        assert len(gs.nodes) > 0

    async def test_ingest_with_embedder(self):
        emb = MockEmbeddingProvider()
        from loom.knowledge.retrievers import InMemoryVectorStore

        vs = InMemoryVectorStore()
        kb = KnowledgeBase(embedder=emb, vector_store=vs)
        await kb.ingest([Document(id="d1", content="Python is great")])
        results = await kb.query("Python")
        assert len(results) > 0
