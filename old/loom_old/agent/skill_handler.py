"""
SkillHandlerMixin - 技能管理

处理技能加载、激活、上下文构建等功能。

从 core.py 拆分，遵循单一职责原则。
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class SkillHandlerMixin:
    """
    技能处理混入类

    提供技能相关的所有功能：
    - 技能上下文构建
    - 技能激活（三种形态）
    - 相关技能加载
    """

    # 类型提示（由 Agent 类提供）
    skill_registry: Any
    skill_activator: Any
    config: Any
    _active_skills: set[str]

    async def _build_skill_context(self) -> str:
        """
        构建 Skill 上下文（用于 Discovery 层）

        返回所有启用 Skills 的元数据，让 LLM 知道有哪些 Skills 可用。
        """
        if not self.skill_registry or not self.config.enabled_skills:
            return ""

        lines = ["## Available Skills\n"]

        for skill_id in self.config.enabled_skills:
            try:
                skill_def = await self.skill_registry.get_skill(skill_id)
                if skill_def:
                    lines.append(f"- **{skill_def.name}**: {skill_def.description}")
                    if skill_def.required_tools:
                        tools_str = ", ".join(skill_def.required_tools)
                        lines.append(f"  - Required Tools: {tools_str}")
            except Exception:
                continue

        if len(lines) == 1:
            return ""

        return "\n".join(lines)

    async def _activate_skills(self, task_description: str) -> dict[str, Any]:
        """
        激活与任务相关的技能

        通过 INJECTION 模式将技能指令注入 system_prompt。
        """
        result: dict[str, Any] = {"injected_instructions": []}

        if not self.skill_activator or not self.skill_registry:
            return result

        try:
            # 获取技能元数据
            skill_metadata = []
            if hasattr(self.skill_registry, "get_all_metadata"):
                skill_metadata = await self.skill_registry.get_all_metadata()

            # 使用 LLM 查找相关技能
            relevant_skill_ids = await self.skill_activator.find_relevant_skills(
                task_description=task_description,
                skill_metadata=skill_metadata,
                max_skills=5,
            )

            # 激活每个相关技能
            for skill_id in relevant_skill_ids:
                skill_def = await self.skill_registry.get_skill(skill_id)
                if not skill_def:
                    continue

                activation_result = await self.skill_activator.activate(skill_def)
                if activation_result.success and activation_result.content:
                    result["injected_instructions"].append(activation_result.content)

        except Exception as e:
            print(f"Error activating skills: {e}")

        return result

    async def _activate_skill(self, skill_id: str) -> dict[str, Any]:
        """
        激活单个 Skill 并验证依赖

        流程：
        1. 检查 skill 是否在 enabled_skills 中
        2. 检查是否已激活
        3. 验证绑定的 tools 是否可用
        4. 激活 Skill
        5. 记录激活状态
        """
        # 检查是否启用
        if skill_id not in self.config.enabled_skills:
            return {"success": False, "error": f"Skill '{skill_id}' not in enabled_skills"}

        # 检查是否已激活
        if skill_id in self._active_skills:
            return {"success": True, "already_active": True}

        if not self.skill_activator or not self.skill_registry:
            return {"success": False, "error": "SkillActivator or SkillRegistry not initialized"}

        try:
            skill_def = await self.skill_registry.get_skill(skill_id)
            if not skill_def:
                return {"success": False, "error": f"Skill '{skill_id}' not found"}

            from loom.tools.models import ActivationResult

            result: ActivationResult = await self.skill_activator.activate(
                skill=skill_def,
                tool_manager=getattr(self, "sandbox_manager", None),
                event_bus=getattr(self, "event_bus", None),
            )

            if result.success:
                self._active_skills.add(skill_id)

            return {
                "success": result.success,
                "mode": result.mode,
                "content": result.content,
                "error": result.error,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _load_relevant_skills(self, task_description: str) -> dict[str, Any]:
        """
        加载并激活与任务相关的Skills

        使用 Progressive Disclosure + LLM 智能判断
        """
        if not self.skill_activator:
            return {"injected_instructions": [], "compiled_tools": [], "instantiated_nodes": []}

        return await self._activate_skills(task_description)
