"""
Tests for loom/tools/skills/filesystem_loader.py
"""

import tempfile
from pathlib import Path

import pytest

from loom.tools.skills.filesystem_loader import FilesystemSkillLoader


@pytest.fixture
def skills_dir(tmp_path):
    """Create a temporary skills directory with sample skills."""
    # Skill with full frontmatter
    skill1 = tmp_path / "code_review"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text(
        "---\nname: Code Review\ndescription: Review code quality\nrequired_tools:\n  - bash\n---\nReview the code carefully.",
        encoding="utf-8",
    )
    refs = skill1 / "references"
    refs.mkdir()
    (refs / "style_guide.md").write_text("# Style Guide\nUse PEP8.", encoding="utf-8")

    # Skill without frontmatter
    skill2 = tmp_path / "simple_skill"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("Just instructions, no frontmatter.", encoding="utf-8")

    # Directory without SKILL.md (should be ignored)
    (tmp_path / "not_a_skill").mkdir()

    return tmp_path


class TestFilesystemSkillLoaderInit:
    def test_valid_dir(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        assert loader.skills_dir == skills_dir

    def test_nonexistent_dir(self):
        with pytest.raises(ValueError, match="does not exist"):
            FilesystemSkillLoader("/nonexistent/path")

    def test_accepts_string(self, skills_dir):
        loader = FilesystemSkillLoader(str(skills_dir))
        assert loader.skills_dir == skills_dir


class TestLoadSkill:
    async def test_load_existing(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        skill = await loader.load_skill("code_review")
        assert skill is not None
        assert skill.name == "Code Review"
        assert skill.description == "Review code quality"
        assert "Review the code carefully" in skill.instructions
        assert "bash" in skill.required_tools
        assert "style_guide.md" in skill.references

    async def test_load_nonexistent(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        skill = await loader.load_skill("nonexistent")
        assert skill is None

    async def test_load_no_frontmatter(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        skill = await loader.load_skill("simple_skill")
        assert skill is not None
        assert skill.name == "simple_skill"  # falls back to dir name
        assert "Just instructions" in skill.instructions


class TestListSkills:
    async def test_list_all(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        skills = await loader.list_skills()
        names = {s.skill_id for s in skills}
        assert "code_review" in names
        assert "simple_skill" in names
        assert "not_a_skill" not in names

    async def test_list_metadata(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        metadata = await loader.list_skill_metadata()
        ids = {m["skill_id"] for m in metadata}
        assert "code_review" in ids
        assert metadata[0]["source"] == "filesystem"


class TestParseFrontmatter:
    def test_with_frontmatter(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        fm, body = loader._parse_frontmatter("---\nname: Test\n---\nBody content")
        assert fm["name"] == "Test"
        assert body == "Body content"

    def test_no_frontmatter(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        fm, body = loader._parse_frontmatter("Just plain text")
        assert fm == {}
        assert body == "Just plain text"

    def test_incomplete_frontmatter(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        fm, body = loader._parse_frontmatter("---\nname: Test\nno closing")
        assert fm == {}

    def test_invalid_yaml(self, skills_dir):
        loader = FilesystemSkillLoader(skills_dir)
        fm, body = loader._parse_frontmatter("---\n: invalid: yaml: {{{\n---\nBody")
        assert fm == {}
