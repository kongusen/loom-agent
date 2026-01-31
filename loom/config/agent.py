"""
Agent Configuration - 可继承的配置体系

基于第12.5节设计：分形继承规则
"""

from dataclasses import dataclass, field
from typing import Set


@dataclass
class AgentConfig:
    """
    Agent 配置 - 支持继承和增量修改

    设计原则：
    - 显式声明继承规则
    - 支持增量修改（添加/移除）
    - 符合分形架构的自相似性

    继承规则（12.5节）：
    - enabled_skills: 继承父的，可添加/移除
    - extra_tools: 继承父的，可添加/移除
    """

    # Skill 配置
    enabled_skills: Set[str] = field(default_factory=set)
    disabled_skills: Set[str] = field(default_factory=set)

    # 工具配置
    extra_tools: Set[str] = field(default_factory=set)
    disabled_tools: Set[str] = field(default_factory=set)

    # 激活模式
    skill_activation_mode: str = "hybrid"  # hybrid, explicit, auto

    @classmethod
    def inherit(
        cls,
        parent: "AgentConfig",
        add_skills: Set[str] | None = None,
        remove_skills: Set[str] | None = None,
        add_tools: Set[str] | None = None,
        remove_tools: Set[str] | None = None,
    ) -> "AgentConfig":
        """
        从父配置继承，支持增量修改

        Args:
            parent: 父配置
            add_skills: 要添加的 Skills
            remove_skills: 要移除的 Skills
            add_tools: 要添加的工具
            remove_tools: 要移除的工具

        Returns:
            新的配置实例
        """
        add_skills = add_skills or set()
        remove_skills = remove_skills or set()
        add_tools = add_tools or set()
        remove_tools = remove_tools or set()

        return cls(
            # Skills: 继承 + 添加 - 移除
            enabled_skills=((parent.enabled_skills | add_skills) - remove_skills),
            disabled_skills=parent.disabled_skills | remove_skills,
            # Tools: 继承 + 添加 - 移除
            extra_tools=((parent.extra_tools | add_tools) - remove_tools),
            disabled_tools=parent.disabled_tools | remove_tools,
            # 激活模式继承
            skill_activation_mode=parent.skill_activation_mode,
        )

    def merge(self, other: "AgentConfig") -> "AgentConfig":
        """
        合并两个配置

        Args:
            other: 另一个配置

        Returns:
            合并后的新配置
        """
        return AgentConfig(
            enabled_skills=self.enabled_skills | other.enabled_skills,
            disabled_skills=self.disabled_skills | other.disabled_skills,
            extra_tools=self.extra_tools | other.extra_tools,
            disabled_tools=self.disabled_tools | other.disabled_tools,
            skill_activation_mode=other.skill_activation_mode,
        )
