"""
Loom Skill System - 核心数据模型

基于Anthropic的Claude Skills定义，支持：
1. 数据库配置
2. 文件系统格式（SKILL.md）
3. 统一接口
4. Skill 三种激活形态（第十一章修订方案）

Skill 三种形态：
- 形态 1: 知识注入（默认）- 注入 system_prompt，零额外 LLM 调用
- 形态 2: 脚本编译为 Tool - 脚本编译为可直接调用的 Tool，走沙盒
- 形态 3: 实例化为 SkillAgentNode - 独立的多轮 LLM 交互（极少）
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SkillActivationMode(str, Enum):
    """
    Skill 激活模式（第十一章修订方案）

    三种形态：
    - INJECTION: 知识注入（默认，90%）- 注入 system_prompt
    - COMPILATION: 脚本编译为 Tool（8%）- 脚本编译为可直接调用的 Tool
    - INSTANTIATION: 实例化为 SkillAgentNode（2%）- 独立的多轮 LLM 交互
    """

    INJECTION = "injection"  # 知识注入（默认）
    COMPILATION = "compilation"  # 脚本编译为 Tool
    INSTANTIATION = "instantiation"  # 实例化为 SkillAgentNode


@dataclass
class SkillDefinition:
    """
    统一的Skill定义

    Skill是比Tool更高层次的概念，是包含指令、脚本和资源的完整工作流包。

    属性：
        skill_id: 唯一标识
        name: 技能名称
        description: 描述（用于激活判断）
        activation_criteria: 激活条件（何时使用此Skill）
        instructions: 执行指令（Markdown格式）
        scripts: 脚本字典 {filename: content}
        references: 参考资料字典 {filename: content}
        required_tools: 需要的工具列表
        metadata: 其他元数据
        source: 来源类型（database/filesystem）
    """

    skill_id: str
    name: str
    description: str
    instructions: str
    activation_criteria: str = ""
    scripts: dict[str, str] = field(default_factory=dict)
    references: dict[str, str] = field(default_factory=dict)
    required_tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"

    def get_full_instructions(self) -> str:
        """
        获取完整的指令文本

        包含：
        1. 基础指令
        2. 脚本列表
        3. 参考资料列表

        Returns:
            完整的指令文本
        """
        parts = [f"# Skill: {self.name}\n"]
        parts.append(f"**Description:** {self.description}\n")

        if self.activation_criteria:
            parts.append(f"**Activation:** {self.activation_criteria}\n")

        parts.append("\n## Instructions\n")
        parts.append(self.instructions)

        if self.scripts:
            parts.append("\n## Available Scripts\n")
            for filename in self.scripts:
                parts.append(f"- `{filename}`\n")

        if self.references:
            parts.append("\n## Available References\n")
            for filename in self.references:
                parts.append(f"- `{filename}`\n")

        if self.required_tools:
            parts.append("\n## Required Tools\n")
            for tool in self.required_tools:
                parts.append(f"- `{tool}`\n")

        return "".join(parts)

    def get_metadata_summary(self) -> dict[str, Any]:
        """
        获取元数据摘要（用于Progressive Disclosure第一阶段）

        Returns:
            包含name和description的字典
        """
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "activation_criteria": self.activation_criteria,
            "source": self.source,
        }


@dataclass
class ActivationResult:
    """
    Skill 激活结果

    用于依赖验证机制（第12章 12.3.4）
    """

    success: bool
    skill_id: str
    mode: SkillActivationMode

    # 成功时的数据
    content: str | None = None  # Form 1: 注入内容
    tool_names: list[str] | None = None  # Form 2: 工具名称
    node: Any | None = None  # Form 3: 节点实例

    # 失败时的信息
    error: str | None = None
    missing_tools: list[str] | None = None
