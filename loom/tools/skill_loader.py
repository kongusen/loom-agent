"""
Filesystem Skill Loader - 从文件系统加载SKILL.md格式的Skills

支持标准的Claude Skills格式：
skills/
└── skill_name/
    ├── SKILL.md
    ├── scripts/
    └── references/
"""

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .loader import SkillLoader
from .models import SkillDefinition


class FilesystemSkillLoader(SkillLoader):
    """
    从文件系统加载Skills

    扫描指定目录，解析SKILL.md文件。
    """

    def __init__(self, skills_dir: str | Path):
        """
        初始化文件系统加载器

        Args:
            skills_dir: Skills目录路径
        """
        self.skills_dir = Path(skills_dir)
        if not self.skills_dir.exists():
            raise ValueError(f"Skills directory does not exist: {skills_dir}")

    async def load_skill(self, skill_id: str) -> SkillDefinition | None:
        """加载单个Skill"""
        skill_path = self.skills_dir / skill_id
        if not skill_path.exists():
            return None

        return await self._parse_skill_folder(skill_path)

    async def list_skills(self) -> list[SkillDefinition]:
        """列出所有Skills"""
        skills = []
        for item in self.skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skill = await self._parse_skill_folder(item)
                if skill:
                    skills.append(skill)
        return skills

    async def list_skill_metadata(self) -> list[dict]:
        """列出所有Skills的元数据"""
        metadata_list = []
        for item in self.skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                metadata = await self._parse_skill_metadata(item)
                if metadata:
                    metadata_list.append(metadata)
        return metadata_list

    async def _parse_skill_metadata(self, skill_path: Path) -> dict | None:
        """
        解析Skill元数据（只读取YAML frontmatter）

        Args:
            skill_path: Skill文件夹路径

        Returns:
            元数据字典
        """
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            return None

        try:
            content = skill_md.read_text(encoding="utf-8")
            frontmatter, _ = self._parse_frontmatter(content)

            return {
                "skill_id": skill_path.name,
                "name": frontmatter.get("name", skill_path.name),
                "description": frontmatter.get("description", ""),
                "source": "filesystem",
            }
        except Exception as e:
            print(f"Error parsing skill metadata {skill_path}: {e}")
            return None

    async def _parse_skill_folder(self, skill_path: Path) -> SkillDefinition | None:
        """
        解析完整的Skill文件夹

        Args:
            skill_path: Skill文件夹路径

        Returns:
            SkillDefinition对象
        """
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            return None

        try:
            # 1. 解析SKILL.md
            content = skill_md.read_text(encoding="utf-8")
            frontmatter, instructions = self._parse_frontmatter(content)

            # 2. 加载references (可选)
            references = {}
            refs_dir = skill_path / "references"
            if refs_dir.exists():
                for ref_file in refs_dir.iterdir():
                    if ref_file.is_file():
                        references[ref_file.name] = ref_file.read_text(encoding="utf-8")

            # 3. 构建SkillDefinition (简化版本)
            return SkillDefinition(
                skill_id=skill_path.name,
                name=frontmatter.get("name", skill_path.name),
                description=frontmatter.get("description", ""),
                instructions=instructions,
                required_tools=frontmatter.get("required_tools", []),
                references=references,
                metadata=frontmatter,
                source="filesystem",
            )

        except Exception as e:
            print(f"Error parsing skill {skill_path}: {e}")
            return None

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """
        解析YAML frontmatter

        Args:
            content: SKILL.md文件内容

        Returns:
            (frontmatter字典, 剩余内容)
        """
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        try:
            frontmatter = yaml.safe_load(parts[1]) or {}
            instructions = parts[2].strip()
            return frontmatter, instructions
        except yaml.YAMLError:
            return {}, content
