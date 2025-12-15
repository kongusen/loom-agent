"""
Skill - Agent 技能定义

技能是 Agent 可以学习和使用的专业能力模块。
"""

from __future__ import annotations

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class SkillMetadata:
    """技能元数据（第一层：索引信息）"""

    name: str  # 技能名称（唯一标识）
    description: str  # 简短描述（1-2句话，~50 tokens）
    category: str  # 分类（tools, analysis, communication, etc.）
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他技能
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillMetadata:
        """从字典创建"""
        return cls(
            name=data["name"],
            description=data["description"],
            category=data.get("category", "general"),
            version=data.get("version", "1.0.0"),
            author=data.get("author"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            enabled=data.get("enabled", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "enabled": self.enabled,
        }

    def to_index_string(self) -> str:
        """生成索引字符串（用于系统提示）"""
        deps = f" (requires: {', '.join(self.dependencies)})" if self.dependencies else ""
        return f"- **{self.name}**: {self.description}{deps}"


@dataclass
class Skill:
    """
    完整技能定义

    技能结构：
    ```
    skills/
      my_skill/
        skill.yaml          # 元数据 + 快速指南
        SKILL.md           # 详细文档（第二层）
        resources/         # 附加资源（第三层）
          examples.json
          templates/
    ```
    """

    metadata: SkillMetadata
    path: Path
    quick_guide: Optional[str] = None  # 快速指南（~200 tokens）
    detailed_doc: Optional[str] = None  # 详细文档（第二层，按需加载）
    resources: Dict[str, Path] = field(default_factory=dict)  # 附加资源路径

    @classmethod
    def from_directory(cls, skill_dir: Path) -> Skill:
        """
        从目录加载技能

        Args:
            skill_dir: 技能目录路径

        Returns:
            Skill 实例

        Raises:
            FileNotFoundError: 如果 skill.yaml 不存在
            ValueError: 如果格式错误
        """
        skill_yaml = skill_dir / "skill.yaml"
        if not skill_yaml.exists():
            raise FileNotFoundError(f"skill.yaml not found in {skill_dir}")

        # 加载元数据
        with open(skill_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        metadata = SkillMetadata.from_dict(data["metadata"])
        quick_guide = data.get("quick_guide")

        # 扫描资源
        resources = {}
        resources_dir = skill_dir / "resources"
        if resources_dir.exists():
            for resource_file in resources_dir.rglob("*"):
                if resource_file.is_file():
                    rel_path = resource_file.relative_to(resources_dir)
                    resources[str(rel_path)] = resource_file

        return cls(
            metadata=metadata,
            path=skill_dir,
            quick_guide=quick_guide,
            resources=resources,
        )

    def load_detailed_doc(self) -> str:
        """
        加载详细文档（第二层，按需加载）

        Returns:
            详细文档内容
        """
        if self.detailed_doc:
            return self.detailed_doc

        skill_md = self.path / "SKILL.md"
        if skill_md.exists():
            with open(skill_md, "r", encoding="utf-8") as f:
                self.detailed_doc = f.read()
        else:
            self.detailed_doc = f"# {self.metadata.name}\n\n{self.metadata.description}"

        return self.detailed_doc

    def get_resource_path(self, resource_name: str) -> Optional[Path]:
        """
        获取资源文件路径

        Args:
            resource_name: 资源名称（相对路径）

        Returns:
            资源文件路径，如果不存在则返回 None
        """
        return self.resources.get(resource_name)

    def to_system_prompt_entry(self) -> str:
        """
        生成系统提示条目（第一层）

        格式：
        ```
        - **skill_name**: Brief description
          Quick guide: [1-2 sentences]
          📄 Details: `cat skills/skill_name/SKILL.md`
          📦 Resources: `ls skills/skill_name/resources/`
        ```
        """
        lines = [
            f"- **{self.metadata.name}**: {self.metadata.description}",
        ]

        if self.quick_guide:
            lines.append(f"  💡 Quick: {self.quick_guide}")

        lines.append(f"  📄 Details: `cat {self.path / 'SKILL.md'}`")

        if self.resources:
            lines.append(f"  📦 Resources: `ls {self.path / 'resources'}/`")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"Skill(name='{self.metadata.name}', category='{self.metadata.category}', enabled={self.metadata.enabled})"


__all__ = [
    "SkillMetadata",
    "Skill",
]
