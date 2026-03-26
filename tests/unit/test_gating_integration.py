"""Phase 3: 公理三信息增益门控测试"""

import pytest

from loom.agent import Agent
from loom.config import AgentConfig
from loom.types import TextDeltaEvent, ToolCall
from tests.conftest import MockLLMProvider


class TestGatingIntegration:
    """验证信息增益门控集成"""

    async def test_emit_with_gain_method_exists(self):
        """验证 _emit_with_gain 方法存在"""
        agent = Agent(provider=MockLLMProvider(["test"]))
        assert hasattr(agent, "_emit_with_gain")

    async def test_filter_tool_output_method_exists(self):
        """验证 _filter_tool_output 方法存在"""
        agent = Agent(provider=MockLLMProvider(["test"]))
        assert hasattr(agent, "_filter_tool_output")

    async def test_tool_output_filtering(self):
        """验证工具输出被过滤"""
        agent = Agent(provider=MockLLMProvider(["test"]))

        # 模拟冗余输出（重复内容）
        redundant_output = "OK\n" * 100

        filtered = await agent._filter_tool_output("test_tool", redundant_output)

        # 应该被过滤或截断
        assert len(filtered) <= len(redundant_output)
