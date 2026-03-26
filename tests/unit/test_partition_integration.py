"""Phase 1: 公理一完整接入测试"""

import pytest

from loom.agent import Agent
from loom.config import AgentConfig
from loom.types import ToolCall
from tests.conftest import MockLLMProvider


class TestPartitionIntegration:
    """验证 Agent 使用所有 5 个分区"""

    async def test_build_messages_uses_all_partitions(self):
        """验证 _build_messages 更新所有 5 个分区"""
        llm = MockLLMProvider(["test response"])
        agent = Agent(provider=llm, config=AgentConfig(max_steps=1))
        agent._goal = "test goal"

        messages = await agent._build_messages()

        # 验证所有分区都有内容或被更新
        assert agent.partition_mgr.partitions["system"].content != ""
        assert agent.partition_mgr.partitions["working"].content != ""
        # memory/skill/history 可能为空，但应该被更新过
        assert "system" in agent.partition_mgr.partitions
        assert "memory" in agent.partition_mgr.partitions
        assert "skill" in agent.partition_mgr.partitions
        assert "history" in agent.partition_mgr.partitions

    async def test_working_partition_contains_goal(self):
        """验证 working 分区包含当前目标"""
        llm = MockLLMProvider(["test"])
        agent = Agent(provider=llm)
        agent._goal = "my test goal"

        await agent._build_messages()

        working_content = agent.partition_mgr.partitions["working"].content
        assert "my test goal" in working_content

    async def test_working_partition_updates_on_tool_execution(self):
        """验证工具执行后 working 分区更新"""
        llm = MockLLMProvider(["test"])
        agent = Agent(provider=llm)

        # 执行工具
        tc = ToolCall(id="test-1", name="test_tool", arguments='{"arg": "value"}')
        await agent._execute_tool(tc)

        # 验证 working 分区包含工具记录
        working = agent.partition_mgr.partitions["working"].content
        assert "test_tool" in working

    async def test_context_to_messages_includes_all_partitions(self):
        """验证 _context_to_messages 包含所有分区"""
        llm = MockLLMProvider(["test"])
        agent = Agent(provider=llm)

        # 设置分区内容
        agent.partition_mgr.update_partition("system", "system content")
        agent.partition_mgr.update_partition("working", "working content")
        agent.partition_mgr.update_partition("memory", "memory content")
        agent.partition_mgr.update_partition("skill", "skill content")

        messages = agent._context_to_messages()

        # 第一个消息应该是 SystemMessage，包含前 4 个分区
        system_msg = messages[0]
        assert "[SYSTEM]" in system_msg.content
        assert "[WORKING]" in system_msg.content
        assert "[MEMORY]" in system_msg.content
        assert "[SKILL]" in system_msg.content
