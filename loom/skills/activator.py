"""
Skill Activator - 智能Skill激活器

使用LLM判断哪些Skills与任务相关，实现Progressive Disclosure。
"""

from typing import Any

from loom.providers.llm.interface import LLMProvider


class SkillActivator:
    """
    智能Skill激活器

    使用LLM判断Skills与任务的相关性，避免加载无关的Skills。
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        初始化激活器

        Args:
            llm_provider: LLM提供者（用于判断相关性）
        """
        self.llm_provider = llm_provider

    async def find_relevant_skills(
        self,
        task_description: str,
        skill_metadata: list[dict[str, Any]],
        max_skills: int = 5,
    ) -> list[str]:
        """
        查找与任务相关的Skills（Progressive Disclosure第一阶段）

        只使用metadata（name + description）判断相关性，不加载完整Skill。

        Args:
            task_description: 任务描述
            skill_metadata: Skills元数据列表
            max_skills: 最多返回的Skills数量

        Returns:
            相关的skill_id列表
        """
        if not skill_metadata:
            return []

        # 构建判断提示词
        skills_info = "\n".join(
            [
                f"{i+1}. {meta['name']}: {meta['description']}"
                for i, meta in enumerate(skill_metadata)
            ]
        )

        prompt = f"""Given the following task and available skills, identify which skills are most relevant to complete the task.

Task: {task_description}

Available Skills:
{skills_info}

Instructions:
- Select up to {max_skills} most relevant skills
- Only select skills that are directly useful for this specific task
- If no skills are relevant, return "NONE"
- Return only the skill numbers (e.g., "1, 3, 5")

Relevant skill numbers:"""

        messages = [{"role": "user", "content": prompt}]

        # 调用LLM判断
        try:
            response = await self.llm_provider.chat(messages)
            result = response.content.strip()

            if result.upper() == "NONE":
                return []

            # 解析返回的skill编号
            selected_indices = []
            for part in result.split(","):
                try:
                    idx = int(part.strip()) - 1  # 转换为0-based索引
                    if 0 <= idx < len(skill_metadata):
                        selected_indices.append(idx)
                except ValueError:
                    continue

            # 返回对应的skill_id
            return [skill_metadata[idx]["skill_id"] for idx in selected_indices]

        except Exception as e:
            print(f"Error in skill activation: {e}")
            # 降级策略：返回前几个Skills
            return [meta["skill_id"] for meta in skill_metadata[:max_skills]]
