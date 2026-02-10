"""
Context Sources Unit Tests

测试 7 大上下文源的实现
"""

import pytest

from loom.context.sources import (
    AgentOutputSource,
    PromptSource,
    SkillSource,
    ToolSource,
    UserInputSource,
)
from loom.memory import EstimateCounter


class TestUserInputSource:
    """测试用户输入源"""

    @pytest.fixture
    def token_counter(self):
        return EstimateCounter()

    @pytest.mark.asyncio
    async def test_collect_empty(self, token_counter):
        """测试空输入"""
        source = UserInputSource()
        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 0

    @pytest.mark.asyncio
    async def test_collect_with_input(self, token_counter):
        """测试有输入"""
        source = UserInputSource("Hello, world!")
        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 1
        assert blocks[0].content == "Hello, world!"
        assert blocks[0].role == "user"
        assert blocks[0].priority == 1.0
        assert blocks[0].compressible is False

    @pytest.mark.asyncio
    async def test_set_input(self, token_counter):
        """测试设置输入"""
        source = UserInputSource()
        source.set_input("New input")
        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 1
        assert blocks[0].content == "New input"

    def test_source_name(self):
        """测试源名称"""
        source = UserInputSource()
        assert source.source_name == "user_input"


class TestAgentOutputSource:
    """测试Agent输出源"""

    @pytest.fixture
    def token_counter(self):
        return EstimateCounter()

    @pytest.mark.asyncio
    async def test_collect_empty(self, token_counter):
        """测试空输出"""
        source = AgentOutputSource()
        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 0

    @pytest.mark.asyncio
    async def test_add_and_collect(self, token_counter):
        """测试添加和收集输出"""
        source = AgentOutputSource()
        source.add_output("First output", "message")
        source.add_output("Second output", "thinking")

        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 2
        assert blocks[0].role == "assistant"

    @pytest.mark.asyncio
    async def test_clear(self, token_counter):
        """测试清空输出"""
        source = AgentOutputSource()
        source.add_output("Output")
        source.clear()

        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 0

    def test_source_name(self):
        """测试源名称"""
        source = AgentOutputSource()
        assert source.source_name == "agent_output"


class TestPromptSource:
    """测试系统提示词源"""

    @pytest.fixture
    def token_counter(self):
        return EstimateCounter()

    @pytest.mark.asyncio
    async def test_collect_empty(self, token_counter):
        """测试空提示词"""
        source = PromptSource()
        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 0

    @pytest.mark.asyncio
    async def test_collect_with_prompt(self, token_counter):
        """测试有提示词"""
        source = PromptSource("You are a helpful assistant.")
        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 1
        assert blocks[0].role == "system"
        assert blocks[0].compressible is False

    def test_source_name(self):
        """测试源名称"""
        source = PromptSource()
        assert source.source_name == "system_prompt"


class TestToolSource:
    """测试工具定义源"""

    @pytest.fixture
    def token_counter(self):
        return EstimateCounter()

    @pytest.mark.asyncio
    async def test_collect_no_manager(self, token_counter):
        """测试无工具管理器"""
        source = ToolSource()
        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 0

    def test_source_name(self):
        """测试源名称"""
        source = ToolSource()
        assert source.source_name == "tools"


class TestSkillSource:
    """测试技能定义源"""

    @pytest.fixture
    def token_counter(self):
        return EstimateCounter()

    @pytest.mark.asyncio
    async def test_collect_no_skills(self, token_counter):
        """测试无激活技能"""
        source = SkillSource()
        blocks = await source.collect(
            query="test",
            token_budget=1000,
            token_counter=token_counter,
        )
        assert len(blocks) == 0

    def test_activate_deactivate(self):
        """测试激活和停用技能"""
        source = SkillSource()
        source.activate_skill("skill-1")
        assert "skill-1" in source._active_skill_ids

        source.deactivate_skill("skill-1")
        assert "skill-1" not in source._active_skill_ids

    def test_source_name(self):
        """测试源名称"""
        source = SkillSource()
        assert source.source_name == "skills"
