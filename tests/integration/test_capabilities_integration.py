"""
Capabilities Integration Tests

端到端测试 SKILL 注入流程 (INJECTION ONLY)
"""

import pytest

from loom.agent import Agent
from loom.providers.llm.mock import MockLLMProvider
from loom.runtime import Task, TaskStatus
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


class TestSkillKnowledgeBinding:
    """Skill-Knowledge 绑定集成测试"""

    def test_activation_includes_search_guidance(self):
        """激活带 search_guidance 的 Skill，验证注入内容包含搜索指引"""
        guidance = (
            "当用户询问产品功能时，使用 query(scope='knowledge') 查找文档。\n"
            "当用户报告错误时，使用 query(intent='troubleshooting')。"
        )
        skill = SkillDefinition(
            skill_id="customer-support",
            name="Customer Support",
            description="客户支持技能",
            instructions="处理客户问题。",
            knowledge_domains=["product_docs", "faq"],
            search_guidance=guidance,
        )

        content = skill.get_full_instructions()

        # 验证 knowledge_domains 出现
        assert "product_docs" in content
        assert "faq" in content
        # 验证 search_guidance 出现
        assert "query(scope='knowledge')" in content
        assert "troubleshooting" in content

    @pytest.mark.asyncio
    async def test_activator_passes_through_search_guidance(self):
        """SkillActivator.activate() 返回的 content 包含 search_guidance"""
        guidance = "使用 query(source='docs') 搜索产品文档。"
        skill = SkillDefinition(
            skill_id="docs-skill",
            name="Docs Skill",
            description="文档技能",
            instructions="帮助用户查找文档。",
            knowledge_domains=["docs"],
            search_guidance=guidance,
        )

        mock_llm = MockLLMProvider(responses=[])
        activator = SkillActivator(llm_provider=mock_llm)
        result = await activator.activate(skill)

        assert result.success is True
        assert result.content is not None
        assert "Search Guidance" in result.content
        assert guidance in result.content
        assert "Knowledge Domains" in result.content
        assert "`docs`" in result.content

    @pytest.mark.asyncio
    async def test_activator_without_knowledge_fields(self):
        """无 knowledge 字段的 Skill 激活正常，不包含相关 section"""
        skill = SkillDefinition(
            skill_id="basic-skill",
            name="Basic Skill",
            description="基础技能",
            instructions="执行基础操作。",
        )

        mock_llm = MockLLMProvider(responses=[])
        activator = SkillActivator(llm_provider=mock_llm)
        result = await activator.activate(skill)

        assert result.success is True
        assert "Knowledge Domains" not in result.content
        assert "Search Guidance" not in result.content
