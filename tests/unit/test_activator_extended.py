"""Coverage-boost tests for skills/activator: async paths, semantic, match_all."""

from loom.skills.activator import _semantic_score, match_trigger, match_trigger_async
from loom.types import Skill, SkillTrigger
from tests.conftest import MockEmbeddingProvider


class TestActivatorMatchAll:
    def test_match_all_true_partial(self):
        skill = Skill(
            name="s",
            trigger=SkillTrigger(type="keyword", keywords=["python", "rust"], match_all=True),
            priority=0.8,
        )
        assert match_trigger(skill, "python help") is None

    def test_match_all_true_full(self):
        skill = Skill(
            name="s",
            trigger=SkillTrigger(type="keyword", keywords=["python", "rust"], match_all=True),
            priority=0.8,
        )
        result = match_trigger(skill, "python and rust")
        assert result is not None

    def test_custom_evaluator_zero(self):
        skill = Skill(
            name="c", trigger=SkillTrigger(type="custom", evaluator=lambda t: 0), priority=0.5
        )
        assert match_trigger(skill, "anything") is None

    def test_custom_evaluator_none(self):
        skill = Skill(
            name="c", trigger=SkillTrigger(type="custom", evaluator=lambda t: None), priority=0.5
        )
        assert match_trigger(skill, "anything") is None

    def test_unknown_trigger_type(self):
        skill = Skill(name="u", trigger=SkillTrigger(type="unknown"), priority=0.5)
        assert match_trigger(skill, "test") is None


class TestActivatorAsync:
    async def test_async_no_trigger(self):
        skill = Skill(name="a", priority=0.3)
        result = await match_trigger_async(skill, "anything")
        assert result is not None
        assert result.reason == "always active"

    async def test_async_keyword(self):
        skill = Skill(
            name="k", trigger=SkillTrigger(type="keyword", keywords=["python"]), priority=0.8
        )
        result = await match_trigger_async(skill, "python help")
        assert result is not None

    async def test_async_keyword_no_match(self):
        skill = Skill(
            name="k", trigger=SkillTrigger(type="keyword", keywords=["rust"]), priority=0.8
        )
        result = await match_trigger_async(skill, "python help")
        assert result is None

    async def test_async_semantic_with_embedder(self):
        embedder = MockEmbeddingProvider()
        skill = Skill(
            name="sem",
            trigger=SkillTrigger(type="semantic", keywords=["python"], threshold=0.0),
            priority=0.8,
        )
        result = await match_trigger_async(skill, "python code", embedder=embedder)
        assert result is not None

    async def test_async_semantic_no_match(self):
        embedder = MockEmbeddingProvider()
        skill = Skill(
            name="sem",
            trigger=SkillTrigger(type="semantic", keywords=["python"], threshold=1.1),
            priority=0.8,
        )
        result = await match_trigger_async(skill, "totally different", embedder=embedder)
        assert result is None


class TestSemanticScore:
    async def test_score_returns_float(self):
        embedder = MockEmbeddingProvider()
        trigger = SkillTrigger(type="semantic", keywords=["python"])
        score = await _semantic_score(embedder, trigger, "python code")
        assert isinstance(score, float)

    async def test_score_no_keywords(self):
        embedder = MockEmbeddingProvider()
        trigger = SkillTrigger(type="semantic", keywords=[])
        score = await _semantic_score(embedder, trigger, "test")
        assert score is None
