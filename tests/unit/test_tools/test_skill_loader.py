"""
Skill Loader Unit Tests

测试技能加载器抽象基类
"""

import pytest

from loom.tools.loader import SkillLoader
from loom.tools.models import SkillDefinition


class MockSkillLoader(SkillLoader):
    """测试用的具体实现"""

    def __init__(self):
        self.skills = {
            "skill-1": SkillDefinition(
                skill_id="skill-1",
                name="Skill 1",
                description="First skill",
                instructions="Do task 1",
            ),
            "skill-2": SkillDefinition(
                skill_id="skill-2",
                name="Skill 2",
                description="Second skill",
                instructions="Do task 2",
            ),
        }

    async def load_skill(self, skill_id: str) -> SkillDefinition | None:
        """加载单个技能"""
        return self.skills.get(skill_id)

    async def list_skills(self) -> list[SkillDefinition]:
        """列出所有技能"""
        return list(self.skills.values())

    async def list_skill_metadata(self) -> list[dict]:
        """列出技能元数据"""
        return [skill.get_metadata_summary() for skill in self.skills.values()]


class TestSkillLoader:
    """测试SkillLoader抽象基类"""

    @pytest.mark.asyncio
    async def test_load_skill_exists(self):
        """测试加载存在的技能"""
        loader = MockSkillLoader()
        skill = await loader.load_skill("skill-1")

        assert skill is not None
        assert skill.skill_id == "skill-1"
        assert skill.name == "Skill 1"
        assert skill.description == "First skill"

    @pytest.mark.asyncio
    async def test_load_skill_not_exists(self):
        """测试加载不存在的技能"""
        loader = MockSkillLoader()
        skill = await loader.load_skill("non-existent")

        assert skill is None

    @pytest.mark.asyncio
    async def test_list_skills(self):
        """测试列出所有技能"""
        loader = MockSkillLoader()
        skills = await loader.list_skills()

        assert len(skills) == 2
        assert all(isinstance(skill, SkillDefinition) for skill in skills)
        skill_ids = [skill.skill_id for skill in skills]
        assert "skill-1" in skill_ids
        assert "skill-2" in skill_ids

    @pytest.mark.asyncio
    async def test_list_skill_metadata(self):
        """测试列出技能元数据"""
        loader = MockSkillLoader()
        metadata_list = await loader.list_skill_metadata()

        assert len(metadata_list) == 2
        assert all(isinstance(metadata, dict) for metadata in metadata_list)
        assert all("skill_id" in metadata for metadata in metadata_list)
        assert all("name" in metadata for metadata in metadata_list)
        assert all("description" in metadata for metadata in metadata_list)
