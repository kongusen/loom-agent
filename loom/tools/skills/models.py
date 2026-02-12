"""
Loom Skill System - 核心数据模型

基于 Anthropic 的 Claude Skills 定义，使用知识注入模式：
- 将 Skill 指令注入到 system_prompt

Skills 格式遵循 Anthropic 标准:
skills/
└── skill_name/
    ├── SKILL.md          # YAML frontmatter + 指令
    └── references/       # 可选: 参考资料
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillDefinition:
    """
    统一的 Skill 定义 - Anthropic 标准格式

    Skill 是包含指令和参考资料的能力包，通过注入到 system_prompt 生效。

    属性:
        skill_id: 唯一标识
        name: 技能名称
        description: 描述（用于能力发现）
        instructions: 执行指令（Markdown 格式，SKILL.md 正文）
        required_tools: 需要的工具列表
        references: 参考资料字典 {filename: content}
        metadata: 其他元数据
        source: 来源类型（filesystem）
    """

    skill_id: str
    name: str
    description: str
    instructions: str
    required_tools: list[str] = field(default_factory=list)
    references: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    knowledge_domains: list[str] = field(default_factory=list)
    search_guidance: str = ""

    def get_full_instructions(self) -> str:
        """
        获取注入到 system_prompt 的内容

        Returns:
            格式化的 Skill 指令文本
        """
        parts = [f"# Skill: {self.name}\n"]
        parts.append(f"**Description:** {self.description}\n")
        parts.append("\n## Instructions\n")
        parts.append(self.instructions)

        if self.references:
            parts.append("\n## Available References\n")
            for filename in self.references:
                parts.append(f"- `{filename}`\n")

        if self.required_tools:
            parts.append("\n## Required Tools\n")
            for tool in self.required_tools:
                parts.append(f"- `{tool}`\n")

        if self.knowledge_domains:
            parts.append("\n## Knowledge Domains\n")
            for domain in self.knowledge_domains:
                parts.append(f"- `{domain}`\n")

        if self.search_guidance:
            parts.append("\n## Search Guidance\n")
            parts.append(self.search_guidance)

        return "".join(parts)

    def get_metadata_summary(self) -> dict[str, Any]:
        """
        获取元数据摘要（用于能力发现）

        Returns:
            包含 skill_id, name, description 的字典
        """
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
        }


@dataclass
class ActivationResult:
    """
    Skill 激活结果
    """

    success: bool
    skill_id: str

    # 成功时: 注入内容
    content: str | None = None

    # 激活模式 (INJECTION)
    mode: str | None = None

    # 工具名称列表
    tool_names: list[str] | None = None

    # 关联的节点
    node: Any | None = None

    # 失败时的信息
    error: str | None = None
    missing_tools: list[str] | None = None
