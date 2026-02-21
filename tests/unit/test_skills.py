"""Unit tests for skills module (registry, activator, provider)."""

from loom.skills.activator import match_trigger
from loom.skills.provider import SkillProvider
from loom.skills.registry import SkillRegistry
from loom.types import Skill, SkillTrigger


class TestMatchTrigger:
    def test_keyword_match(self):
        skill = Skill(
            name="code", trigger=SkillTrigger(type="keyword", keywords=["python"]), priority=0.8
        )
        result = match_trigger(skill, "I need python help")
        assert result is not None
        assert result.score > 0

    def test_keyword_no_match(self):
        skill = Skill(
            name="code", trigger=SkillTrigger(type="keyword", keywords=["rust"]), priority=0.8
        )
        assert match_trigger(skill, "python help") is None

    def test_pattern_match(self):
        skill = Skill(
            name="regex", trigger=SkillTrigger(type="pattern", pattern=r"fix\s+bug"), priority=0.5
        )
        result = match_trigger(skill, "please fix bug #123")
        assert result is not None

    def test_custom_evaluator(self):
        skill = Skill(
            name="custom",
            trigger=SkillTrigger(type="custom", evaluator=lambda t: 0.9 if "special" in t else 0),
            priority=0.5,
        )
        result = match_trigger(skill, "special request")
        assert result is not None
        assert result.score > 0

    def test_no_trigger_always_active(self):
        skill = Skill(name="always", priority=0.3)
        result = match_trigger(skill, "anything")
        assert result is not None


class TestSkillRegistry:
    def test_register_and_get(self):
        reg = SkillRegistry()
        skill = Skill(name="code", instructions="help with code")
        reg.register(skill)
        assert reg.get("code") is skill

    def test_always_active_auto_registered(self):
        reg = SkillRegistry()
        reg.register(Skill(name="s1", activation_level="always"))
        assert len(reg.get_active()) == 1

    async def test_activate_keyword(self):
        reg = SkillRegistry()
        reg.register(
            Skill(
                name="py", trigger=SkillTrigger(type="keyword", keywords=["python"]), priority=0.8
            )
        )
        acts = await reg.activate("python help")
        assert len(acts) >= 1

    async def test_on_demand_skipped(self):
        reg = SkillRegistry()
        reg.register(
            Skill(
                name="manual",
                activation_level="on-demand",
                trigger=SkillTrigger(type="keyword", keywords=["x"]),
            )
        )
        acts = await reg.activate("x")
        assert not any(a.skill.name == "manual" for a in acts)


class TestSkillProvider:
    async def test_provides_instructions(self):
        reg = SkillRegistry()
        reg.register(
            Skill(
                name="py",
                instructions="Use python",
                trigger=SkillTrigger(type="keyword", keywords=["python"]),
                priority=0.8,
            )
        )
        provider = SkillProvider(reg)
        frags = await provider.provide("python help", budget=1000)
        assert len(frags) == 1
        assert "python" in frags[0].content.lower()

    async def test_budget_respected(self):
        reg = SkillRegistry()
        reg.register(
            Skill(
                name="big",
                instructions="x" * 5000,
                trigger=SkillTrigger(type="keyword", keywords=["big"]),
                priority=0.8,
            )
        )
        provider = SkillProvider(reg)
        frags = await provider.provide("big", budget=10)
        assert len(frags) == 0
