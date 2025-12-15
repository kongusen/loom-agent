"""
SkillManager - Agent 技能管理器

负责加载、管理和提供技能访问。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set

from loom.skills.skill import Skill, SkillMetadata


class SkillManager:
    """
    技能管理器

    特性：
    - 自动扫描技能目录
    - 三层渐进式披露
    - 依赖解析
    - 技能启用/禁用

    Example:
        ```python
        # 初始化
        skill_mgr = SkillManager("./skills")

        # 获取系统提示（只包含索引）
        system_prompt = skill_mgr.get_system_prompt_section()

        # Agent 按需读取详细信息
        # Claude 会自动使用 bash: cat skills/pdf_analyzer/SKILL.md
        ```
    """

    def __init__(self, skills_dir: str | Path):
        """
        初始化技能管理器

        Args:
            skills_dir: 技能目录路径
        """
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Skill] = {}
        self._loaded = False

        # 确保目录存在
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> None:
        """加载所有技能"""
        if self._loaded:
            return

        self.skills.clear()

        # 扫描技能目录
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            try:
                skill = Skill.from_directory(skill_dir)
                self.skills[skill.metadata.name] = skill
            except Exception as e:
                print(f"[SkillManager] Failed to load skill from {skill_dir}: {e}")

        self._loaded = True
        print(f"[SkillManager] Loaded {len(self.skills)} skills")

    def reload(self) -> None:
        """重新加载所有技能"""
        self._loaded = False
        self.load_all()

    def get_skill(self, name: str) -> Optional[Skill]:
        """
        获取技能

        Args:
            name: 技能名称

        Returns:
            Skill 实例，如果不存在则返回 None
        """
        if not self._loaded:
            self.load_all()

        return self.skills.get(name)

    def list_skills(
        self, category: Optional[str] = None, enabled_only: bool = True
    ) -> List[Skill]:
        """
        列出技能

        Args:
            category: 筛选分类（可选）
            enabled_only: 只返回启用的技能

        Returns:
            技能列表
        """
        if not self._loaded:
            self.load_all()

        skills = list(self.skills.values())

        if enabled_only:
            skills = [s for s in skills if s.metadata.enabled]

        if category:
            skills = [s for s in skills if s.metadata.category == category]

        return skills

    def get_system_prompt_section(
        self, enabled_only: bool = True, include_quick_guide: bool = True
    ) -> str:
        """
        生成系统提示中的技能部分（第一层：索引）

        Args:
            enabled_only: 只包含启用的技能
            include_quick_guide: 包含快速指南

        Returns:
            系统提示文本
        """
        if not self._loaded:
            self.load_all()

        skills = self.list_skills(enabled_only=enabled_only)

        if not skills:
            return ""

        lines = [
            "# Available Skills",
            "",
            "You have access to the following skills. These are specialized capabilities that you can use to solve tasks.",
            "",
            "**Usage**:",
            "- Skills are listed below with brief descriptions",
            "- To learn more about a skill, use: `cat skills/<skill_name>/SKILL.md`",
            "- To access skill resources, use: `ls skills/<skill_name>/resources/`",
            "",
            "**Skills Index**:",
            "",
        ]

        # 按分类分组
        by_category: Dict[str, List[Skill]] = {}
        for skill in skills:
            category = skill.metadata.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(skill)

        # 生成分类列表
        for category, category_skills in sorted(by_category.items()):
            lines.append(f"## {category.title()}")
            lines.append("")

            for skill in category_skills:
                if include_quick_guide:
                    lines.append(skill.to_system_prompt_entry())
                else:
                    lines.append(skill.metadata.to_index_string())
                lines.append("")

        return "\n".join(lines)

    def enable_skill(self, name: str) -> bool:
        """
        启用技能

        Args:
            name: 技能名称

        Returns:
            是否成功
        """
        skill = self.get_skill(name)
        if not skill:
            return False

        skill.metadata.enabled = True
        self._save_skill_metadata(skill)
        return True

    def disable_skill(self, name: str) -> bool:
        """
        禁用技能

        Args:
            name: 技能名称

        Returns:
            是否成功
        """
        skill = self.get_skill(name)
        if not skill:
            return False

        skill.metadata.enabled = False
        self._save_skill_metadata(skill)
        return True

    def create_skill(
        self,
        name: str,
        description: str,
        category: str = "general",
        quick_guide: Optional[str] = None,
        detailed_content: Optional[str] = None,
        **kwargs,
    ) -> Skill:
        """
        创建新技能

        Args:
            name: 技能名称
            description: 描述
            category: 分类
            quick_guide: 快速指南
            detailed_content: 详细文档内容
            **kwargs: 其他元数据字段

        Returns:
            创建的 Skill 实例

        Raises:
            ValueError: 如果技能已存在
        """
        if name in self.skills:
            raise ValueError(f"Skill '{name}' already exists")

        # 创建目录
        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 创建元数据
        metadata = SkillMetadata(
            name=name,
            description=description,
            category=category,
            version=kwargs.get("version", "1.0.0"),
            author=kwargs.get("author"),
            tags=kwargs.get("tags", []),
            dependencies=kwargs.get("dependencies", []),
            enabled=kwargs.get("enabled", True),
        )

        # 保存 skill.yaml
        skill_yaml = {
            "metadata": metadata.to_dict(),
        }
        if quick_guide:
            skill_yaml["quick_guide"] = quick_guide

        with open(skill_dir / "skill.yaml", "w", encoding="utf-8") as f:
            import yaml

            yaml.safe_dump(skill_yaml, f, allow_unicode=True, default_flow_style=False)

        # 创建 SKILL.md
        if detailed_content:
            skill_md_content = detailed_content
        else:
            skill_md_content = f"""# {name}

{description}

## Overview

[Add detailed overview here]

## Usage

[Add usage instructions here]

## Examples

```python
# Add examples here
```

## Notes

- [Add important notes]
"""

        with open(skill_dir / "SKILL.md", "w", encoding="utf-8") as f:
            f.write(skill_md_content)

        # 创建 resources 目录
        (skill_dir / "resources").mkdir(exist_ok=True)

        # 加载新技能
        skill = Skill.from_directory(skill_dir)
        self.skills[name] = skill

        print(f"[SkillManager] Created skill: {name}")
        return skill

    def delete_skill(self, name: str) -> bool:
        """
        删除技能

        Args:
            name: 技能名称

        Returns:
            是否成功
        """
        skill = self.get_skill(name)
        if not skill:
            return False

        # 删除目录
        shutil.rmtree(skill.path)

        # 从内存中移除
        del self.skills[name]

        print(f"[SkillManager] Deleted skill: {name}")
        return True

    def edit_skill_metadata(self, name: str, **updates) -> bool:
        """
        编辑技能元数据

        Args:
            name: 技能名称
            **updates: 要更新的字段

        Returns:
            是否成功
        """
        skill = self.get_skill(name)
        if not skill:
            return False

        # 更新元数据
        for key, value in updates.items():
            if hasattr(skill.metadata, key):
                setattr(skill.metadata, key, value)

        # 保存
        self._save_skill_metadata(skill)
        return True

    def _save_skill_metadata(self, skill: Skill) -> None:
        """保存技能元数据到 skill.yaml"""
        skill_yaml_path = skill.path / "skill.yaml"

        # 读取现有内容
        with open(skill_yaml_path, "r", encoding="utf-8") as f:
            import yaml

            data = yaml.safe_load(f)

        # 更新元数据
        data["metadata"] = skill.metadata.to_dict()

        # 保存
        with open(skill_yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)

    def get_stats(self) -> Dict[str, any]:
        """获取统计信息"""
        if not self._loaded:
            self.load_all()

        total = len(self.skills)
        enabled = len([s for s in self.skills.values() if s.metadata.enabled])
        categories = len(set(s.metadata.category for s in self.skills.values()))

        return {
            "total_skills": total,
            "enabled_skills": enabled,
            "disabled_skills": total - enabled,
            "categories": categories,
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"SkillManager("
            f"dir='{self.skills_dir}', "
            f"total={stats['total_skills']}, "
            f"enabled={stats['enabled_skills']})"
        )


__all__ = [
    "SkillManager",
]
