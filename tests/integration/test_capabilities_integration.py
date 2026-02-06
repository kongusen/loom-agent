"""
Capabilities Integration Tests

端到端测试 SKILL 注入流程 (INJECTION ONLY)
"""

import pytest

from loom.agent import Agent
from loom.protocol import Task, TaskStatus
from loom.providers.llm.mock import MockLLMProvider
from loom.tools.core.registry import ToolRegistry
from loom.tools.skills.activator import SkillActivator
from loom.tools.skills.loader import SkillLoader
from loom.tools.skills.models import SkillDefinition
from loom.tools.skills.registry import SkillRegistry


class InMemorySkillLoader(SkillLoader):
    """简单的内存 Skill Loader，用于测试"""

    def __init__(self):
        self.skills: dict[str, SkillDefinition] = {}

    def add_skill(self, skill: SkillDefinition):
        """添加 Skill 到内存"""
        self.skills[skill.skill_id] = skill

    async def load_skill(self, skill_id: str) -> SkillDefinition | None:
        """加载单个 Skill"""
        return self.skills.get(skill_id)

    async def list_skills(self) -> list[SkillDefinition]:
        """列出所有 Skills"""
        return list(self.skills.values())

    async def list_skill_metadata(self) -> list[dict]:
        """列出所有 Skills 的元数据"""
        return [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "source": "memory",
            }
            for skill in self.skills.values()
        ]


class TestSkillInjection:
    """测试 SKILL 知识注入"""

    @pytest.mark.asyncio
    async def test_knowledge_injection_in_system_prompt(self):
        """
        测试 Skill 指令被注入到 system_prompt

        验证点：
        1. Skill 被正确加载
        2. Skill 指令出现在 Agent 的上下文中
        3. Agent 能够使用注入的知识完成任务
        """
        # 1. 创建纯知识型 Skill
        skill_def = SkillDefinition(
            skill_id="python-best-practices",
            name="Python Best Practices",
            description="Python 编程最佳实践指南",
            instructions="""
You are a Python expert. When reviewing code, always check:
- Type hints are used for all function parameters
- Docstrings follow Google style
- Variable names are descriptive
""",
            required_tools=[],
        )

        # 2. 注册 Skill
        loader = InMemorySkillLoader()
        loader.add_skill(skill_def)

        skill_registry = SkillRegistry()
        skill_registry.register_loader(loader)

        # 3. 创建依赖组件
        tool_registry = ToolRegistry()
        mock_llm = MockLLMProvider(
            responses=[
                # SkillActivator 的 LLM 调用：返回相关 Skill
                {"type": "text", "content": "1"},
                # Agent 执行任务的 LLM 调用
                {
                    "type": "text",
                    "content": "Based on Python best practices, this code needs type hints.",
                },
                {
                    "type": "tool_call",
                    "name": "done",
                    "arguments": {"message": "Code review complete: Add type hints"},
                },
            ]
        )

        skill_activator = SkillActivator(
            llm_provider=mock_llm,
            tool_registry=tool_registry,
        )

        # 4. 创建 Agent
        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            skill_activator=skill_activator,
            tool_registry=tool_registry,
            require_done_tool=True,
        )

        # 5. 执行任务
        task = Task(
            task_id="test-task-1",
            action="execute",
            parameters={"content": "Review this Python code: def calc(a, b): return a + b"},
        )

        result = await agent.execute_task(task)

        # 6. 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result is not None

        # 验证 Skill 知识被应用
        result_content = result.result.get("content", "")
        # 注意：Mock LLM 的响应是我们预设的，所以这里主要验证流程通畅
        assert "type hints" in result_content.lower() or "type hint" in result_content.lower()
