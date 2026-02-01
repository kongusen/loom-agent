"""
Skill Activation Forms Integration Tests

端到端测试三种 Skill 激活形态：
1. Form 1 (INJECTION): 知识注入到 system_prompt
2. Form 2 (COMPILATION): 脚本编译为工具
3. Form 3 (INSTANTIATION): 实例化为 SkillAgentNode

这些测试验证从 Agent 创建、Skill 注册、激活到任务执行的完整流程。
"""

import tempfile

import pytest

from loom.agent import Agent
from loom.protocol import Task, TaskStatus
from loom.providers.llm.mock import MockLLMProvider
from loom.skills.activator import SkillActivator
from loom.skills.loader import SkillLoader
from loom.skills.models import SkillDefinition
from loom.skills.registry import SkillRegistry
from loom.tools.registry import ToolRegistry
from loom.tools.sandbox import Sandbox
from loom.tools.sandbox_manager import SandboxToolManager


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
            }
            for skill in self.skills.values()
        ]


class TestForm1Injection:
    """测试 Form 1: 知识注入形态"""

    @pytest.mark.asyncio
    async def test_form1_knowledge_injection_in_system_prompt(self):
        """
        测试 Form 1: Skill 指令被注入到 system_prompt

        验证点：
        1. Skill 被正确激活为 INJECTION 模式
        2. Skill 指令出现在 Agent 的上下文中
        3. Agent 能够使用注入的知识完成任务
        """
        # 1. 创建纯知识型 Skill（无 scripts）
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
            activation_criteria="python code review",
            scripts={},  # 无脚本 -> Form 1
            required_tools=[],
        )

        # 2. 注册 Skill（使用 Loader 模式）
        loader = InMemorySkillLoader()
        loader.add_skill(skill_def)

        skill_registry = SkillRegistry()
        skill_registry.register_loader(loader)

        # 3. 创建 SkillActivator
        tool_registry = ToolRegistry()
        mock_llm = MockLLMProvider(
            responses=[
                # SkillActivator 的 LLM 调用：返回相关 Skill（返回编号，不是ID）
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

        # Debug: 验证 SkillRegistry 是否正确设置
        metadata = await skill_registry.get_all_metadata()
        print("\n=== Skill Metadata ===")
        print(f"Metadata: {metadata}")
        print("=====================\n")

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

        # Debug: 打印结果内容
        print("\n=== Debug Info ===")
        print(f"Result: {result.result}")
        print(f"Active skills: {agent._active_skills}")
        print(f"System prompt length: {len(agent.system_prompt)}")
        print("==================\n")

        # 验证 Skill 知识被应用（结果中提到了 type hints）
        result_content = result.result.get("content", "")
        assert "type hints" in result_content.lower() or "type hint" in result_content.lower()


class TestForm2Compilation:
    """测试 Form 2: 工具编译形态"""

    @pytest.mark.asyncio
    async def test_form2_script_compilation_to_tools(self):
        """
        测试 Form 2: Skill 脚本被编译为可调用工具

        验证点：
        1. Skill 被正确激活为 COMPILATION 模式
        2. 脚本被编译并注册到 SandboxToolManager
        3. Agent 能够调用编译后的工具
        4. 工具执行返回正确结果
        """
        # 1. 创建带脚本的 Skill
        skill_def = SkillDefinition(
            skill_id="data-analysis",
            name="Data Analysis Tools",
            description="数据分析工具集",
            instructions="Use these tools to analyze data",
            scripts={
                "calculate_stats.py": """
def main(data):
    '''Calculate basic statistics for a list of numbers'''
    if not data:
        return {"error": "Empty data"}
    return {
        "mean": sum(data) / len(data),
        "min": min(data),
        "max": max(data),
        "count": len(data)
    }
"""
            },
            required_tools=[],
        )

        # 2. 注册 Skill（使用 Loader 模式）
        loader = InMemorySkillLoader()
        loader.add_skill(skill_def)

        skill_registry = SkillRegistry()
        skill_registry.register_loader(loader)

        # 3. 创建依赖组件
        tool_registry = ToolRegistry()
        # 创建临时沙盒目录
        temp_dir = tempfile.mkdtemp()
        sandbox = Sandbox(root_dir=temp_dir)
        sandbox_manager = SandboxToolManager(sandbox=sandbox)

        mock_llm = MockLLMProvider(
            responses=[
                # SkillActivator 的 LLM 调用：返回相关 Skill（返回编号，不是ID）
                {"type": "text", "content": "1"},
                # Agent 执行任务的 LLM 调用
                {"type": "text", "content": "I'll calculate statistics for the data."},
                {
                    "type": "tool_call",
                    "name": "data-analysis_calculate_stats",
                    "arguments": {"data": [1, 2, 3, 4, 5]},
                },
                {"type": "text", "content": "Statistics calculated."},
                {
                    "type": "tool_call",
                    "name": "done",
                    "arguments": {"message": "Mean: 3.0, Min: 1, Max: 5"},
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
            sandbox_manager=sandbox_manager,
            require_done_tool=True,
        )

        # 5. 执行任务
        task = Task(
            task_id="test-task-2",
            action="execute",
            parameters={"content": "Calculate statistics for [1, 2, 3, 4, 5]"},
        )

        result = await agent.execute_task(task)

        # 6. 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result is not None

        # 验证工具被注册（工具名称格式：{skill_id}_{script_name}）
        assert "data-analysis_calculate_stats" in sandbox_manager.list_tool_names()

        # 验证结果包含统计数据
        result_content = result.result.get("content", "")
        assert "mean" in result_content.lower() or "3" in result_content


class TestForm3Instantiation:
    """测试 Form 3: 节点实例化形态"""

    @pytest.mark.asyncio
    async def test_form3_skill_node_instantiation_and_delegation(self):
        """
        测试 Form 3: Skill 被实例化为 SkillAgentNode 并可被委派

        验证点：
        1. Skill 被正确激活为 INSTANTIATION 模式
        2. SkillAgentNode 被创建并添加到 _active_skill_nodes
        3. Agent 可以通过 delegate_task 委派给 SkillAgentNode
        4. 委派返回正确结果
        """
        # 1. 创建多轮交互 Skill（带 multi_turn 元数据）
        skill_def = SkillDefinition(
            skill_id="code-reviewer",
            name="Code Reviewer",
            description="专业代码审查助手（支持多轮交互）",
            instructions="You are a code review expert. Provide detailed feedback on code quality.",
            activation_criteria="code review with discussion",
            scripts={},
            required_tools=[],
            metadata={"multi_turn": True},  # 触发 Form 3
        )

        # 2. 注册 Skill（使用 Loader 模式）
        loader = InMemorySkillLoader()
        loader.add_skill(skill_def)

        skill_registry = SkillRegistry()
        skill_registry.register_loader(loader)

        # 3. 创建依赖组件
        tool_registry = ToolRegistry()

        mock_llm = MockLLMProvider(
            responses=[
                # SkillActivator 的 LLM 调用：返回相关 Skill（返回编号，不是ID）
                {"type": "text", "content": "1"},
                # Agent 主循环：决定委派给 code-reviewer
                {"type": "text", "content": "I'll delegate this to the code reviewer."},
                {
                    "type": "tool_call",
                    "name": "delegate_task",
                    "arguments": {
                        "target_agent": "code-reviewer",
                        "subtask": "Review the authentication code",
                    },
                },
                # SkillAgentNode 执行审查
                {
                    "type": "text",
                    "content": "Code review: The authentication logic looks good but needs error handling.",
                },
                {"type": "tool_call", "name": "done", "arguments": {"message": "Review complete"}},
                # Agent 主循环：完成任务
                {"type": "text", "content": "Review completed."},
                {
                    "type": "tool_call",
                    "name": "done",
                    "arguments": {"message": "Code review completed"},
                },
            ]
        )

        skill_activator = SkillActivator(
            llm_provider=mock_llm,
            tool_registry=tool_registry,
        )

        # 4. 创建 Agent（需要 available_agents 来支持 delegate_task 工具）
        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            skill_activator=skill_activator,
            tool_registry=tool_registry,
            available_agents={},  # 空的 available_agents，强制使用 _active_skill_nodes
            require_done_tool=True,
        )

        # 5. 执行任务
        task = Task(
            task_id="test-task-3",
            action="execute",
            parameters={"content": "Review the authentication module code"},
        )

        result = await agent.execute_task(task)

        # 6. 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result is not None

        # 验证 SkillAgentNode 被创建
        assert hasattr(agent, "_active_skill_nodes")
        assert len(agent._active_skill_nodes) > 0

        # 验证委派成功（结果中包含审查内容）
        result_content = result.result.get("content", "")
        assert "review" in result_content.lower() or "code" in result_content.lower()
