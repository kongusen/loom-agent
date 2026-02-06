"""
Skill Activator - Skill 激活控制器

负责协调 Skill 的激活流程：
1. 语义搜索相关 Skill
2. 确定激活模式 (INJECTION only)
3. 执行激活 (获取注入指令)
"""

from typing import Any

from loom.providers.llm.interface import LLMProvider
from loom.tools.core.sandbox_manager import SandboxToolManager

from .models import ActivationResult, SkillDefinition


class SkillActivator:
    """
    Skill 激活协调器
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: Any | None = None,
        tool_manager: SandboxToolManager | None = None,
    ):
        self.llm = llm_provider
        self.tool_registry = tool_registry
        self.tool_manager = tool_manager

    async def find_relevant_skills(
        self,
        task_description: str,
        skill_metadata: list[dict[str, Any]],
        max_skills: int = 5,
    ) -> list[str]:
        """
        查找相关的 Skills (简单实现：关键词匹配)

        目前 Agent.core 中调用此方法。
        使用简单的关键词匹配作为临时方案，直到集成向量搜索。
        """
        if not task_description:
            return []

        # 简单关键词匹配
        keywords = set(task_description.lower().split())
        scored_skills = []

        for m in skill_metadata:
            score = 0
            # 检查 ID 和 description 中的匹配
            text = (m.get("skill_id", "") + " " + m.get("description", "")).lower()
            for kw in keywords:
                if len(kw) > 3 and kw in text:  # 忽略短词
                    score += 1

            if score > 0:
                scored_skills.append((score, m["skill_id"]))

        # 按分数排序
        scored_skills.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored_skills[:max_skills]]

    async def activate(
        self,
        skill: SkillDefinition,
        tool_manager: SandboxToolManager | None = None,
        event_bus: Any | None = None,
    ) -> ActivationResult:
        """
        激活 Skill（统一入口）

        Args:
            skill: Skill 定义
            tool_manager: 工具管理器（用于依赖验证）
            event_bus: 事件总线（可选）

        Returns:
            ActivationResult: 激活结果
        """
        # 1. 验证工具依赖
        missing_tools: list[str] = []
        if skill.required_tools and tool_manager:
            available_tools = set(tool_manager.list_tools())
            for tool_name in skill.required_tools:
                if tool_name not in available_tools:
                    missing_tools.append(tool_name)

        if missing_tools:
            return ActivationResult(
                success=False,
                skill_id=skill.skill_id,
                error=f"Missing required tools: {', '.join(missing_tools)}",
                missing_tools=missing_tools,
            )

        try:
            # 2. 获取注入内容
            content = skill.get_full_instructions()

            # 3. 发布激活事件
            if event_bus:
                await event_bus.publish(
                    "skill.activated",
                    {
                        "skill_id": skill.skill_id,
                        "mode": "INJECTION",
                        "tool_names": list(skill.required_tools) if skill.required_tools else [],
                    },
                )

            return ActivationResult(
                success=True,
                skill_id=skill.skill_id,
                content=content,
                mode="INJECTION",
                tool_names=list(skill.required_tools) if skill.required_tools else None,
            )
        except Exception as e:
            return ActivationResult(
                success=False,
                skill_id=skill.skill_id,
                error=str(e),
            )
