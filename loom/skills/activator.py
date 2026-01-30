"""
Skill Activator - 智能Skill激活器

使用LLM判断哪些Skills与任务相关，实现Progressive Disclosure。

支持三种激活形态（Phase 2）：
- Form 1: 知识注入 (INJECTION) - 注入到 system_prompt
- Form 2: 脚本编译为 Tool (COMPILATION) - 编译为可调用工具
- Form 3: 实例化为 SkillAgentNode (INSTANTIATION) - 独立多轮交互
"""

from typing import Any

from loom.providers.llm.interface import LLMProvider
from loom.skills.models import SkillActivationMode, SkillDefinition
from loom.skills.script_compiler import ScriptCompiler


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

    def determine_activation_mode(
        self,
        skill: SkillDefinition,
    ) -> SkillActivationMode:
        """
        Layer 1: Configuration - 决定 Skill 的激活模式

        决策规则：
        1. 如果 skill.metadata 中指定了 activation_mode，使用指定的模式
        2. 否则，根据 Skill 特征自动判断：
           - 有脚本 (scripts) → COMPILATION
           - 标记为需要多轮交互 (metadata.multi_turn=True) → INSTANTIATION
           - 默认 → INJECTION

        Args:
            skill: Skill 定义

        Returns:
            激活模式
        """
        # 1. 检查是否显式指定了激活模式
        if "activation_mode" in skill.metadata:
            mode_str = skill.metadata["activation_mode"]
            try:
                return SkillActivationMode(mode_str)
            except ValueError:
                # 无效的模式，使用默认
                pass

        # 2. 根据 Skill 特征自动判断
        # 如果有脚本，使用编译模式
        if skill.scripts:
            return SkillActivationMode.COMPILATION

        # 如果标记为需要多轮交互，使用实例化模式
        if skill.metadata.get("multi_turn", False):
            return SkillActivationMode.INSTANTIATION

        # 3. 默认使用知识注入模式
        return SkillActivationMode.INJECTION

    def activate_injection(
        self,
        skill: SkillDefinition,
    ) -> str:
        """
        Layer 3: Activation - Form 1 知识注入

        将 Skill 的完整指令注入到 system_prompt

        Args:
            skill: Skill 定义

        Returns:
            注入的文本内容
        """
        return skill.get_full_instructions()

    async def activate_compilation(
        self,
        skill: SkillDefinition,
        tool_manager: Any,  # SandboxToolManager
    ) -> list[str]:
        """
        Layer 3: Activation - Form 2 脚本编译为 Tool

        将 Skill 的脚本编译为可调用的 Tool，并注册到 ToolManager

        Args:
            skill: Skill 定义
            tool_manager: SandboxToolManager 实例

        Returns:
            注册的 Tool 名称列表

        Raises:
            ValueError: 脚本编译失败
        """
        if not skill.scripts:
            return []

        compiler = ScriptCompiler()
        registered_tools = []

        for script_name, script_content in skill.scripts.items():
            try:
                # 1. 编译脚本为可执行函数
                tool_func = compiler.compile_script(script_content, script_name)

                # 2. 创建 Tool 名称和描述
                tool_name = f"{skill.skill_id}_{script_name.replace('.py', '')}"
                tool_description = (
                    f"Script from skill '{skill.name}': {script_name}\n"
                    f"{skill.description}"
                )

                # 3. 创建 MCP Tool 定义
                from loom.protocol.mcp import MCPToolDefinition

                tool_def = MCPToolDefinition(
                    name=tool_name,
                    description=tool_description,
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                )

                # 4. 注册到 ToolManager
                from loom.tools.sandbox_manager import ToolScope

                await tool_manager.register_tool(
                    name=tool_name,
                    func=tool_func,
                    definition=tool_def,
                    scope=ToolScope.SANDBOXED,
                )

                registered_tools.append(tool_name)

            except Exception as e:
                # 记录错误但继续处理其他脚本
                print(f"Failed to compile script '{script_name}': {e}")
                continue

        return registered_tools

    def activate_instantiation(
        self,
        skill: SkillDefinition,
        event_bus: Any | None = None,
    ) -> Any:  # Returns SkillAgentNode
        """
        Layer 3: Activation - Form 3 实例化为 SkillAgentNode

        创建一个 SkillAgentNode 实例，用于需要独立多轮 LLM 交互的 Skill。
        这是极少数场景（约 2%），使用简化的执行路径。

        Args:
            skill: Skill 定义
            event_bus: 事件总线（用于委派）

        Returns:
            SkillAgentNode 实例

        Raises:
            ValueError: Skill 不适合实例化
        """
        from loom.agent.skill_node import SkillAgentNode

        # 创建 SkillAgentNode 实例
        skill_node = SkillAgentNode(
            skill_id=skill.skill_id,
            skill_definition=skill,
            llm_provider=self.llm_provider,
            event_bus=event_bus,
        )

        return skill_node
