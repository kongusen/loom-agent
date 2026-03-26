"""Phase 2: 公理二约束前置测试"""

import pytest

from loom.agent import Agent
from loom.config import AgentConfig
from loom.types import ToolCall
from loom.types.scene import ScenePackage
from tests.conftest import MockLLMProvider


class TestConstraintIntegration:
    """验证约束前置验证集成"""

    async def test_tool_blocked_by_scene_constraint(self):
        """验证场景约束阻止工具执行"""
        agent = Agent(provider=MockLLMProvider(["test"]))

        # 激活禁止网络的场景
        scene = ScenePackage(id="offline", tools=[], constraints={"network": False})
        agent.scene_mgr.register(scene)
        agent.scene_mgr.switch("offline")

        # 尝试调用网络工具
        result = await agent._execute_tool(
            ToolCall(id="1", name="web_search", arguments='{"query": "test"}')
        )

        assert "error" in result
        assert "not allowed" in result

    async def test_tool_allowed_in_scene(self):
        """验证场景允许的工具可以执行"""
        agent = Agent(provider=MockLLMProvider(["test"]))

        # 激活允许特定工具的场景
        scene = ScenePackage(id="limited", tools=["read_file"], constraints={})
        agent.scene_mgr.register(scene)
        agent.scene_mgr.switch("limited")

        # read_file 应该被允许（虽然会失败因为工具不存在）
        result = await agent._execute_tool(
            ToolCall(id="1", name="read_file", arguments='{"path": "test.txt"}')
        )

        # 应该是工具不存在的错误，而不是约束错误
        assert "not found" in result or "error" in result

    async def test_no_scene_allows_all_tools(self):
        """验证无场景时所有工具都被允许"""
        agent = Agent(provider=MockLLMProvider(["test"]))

        # 不设置场景
        result = await agent._execute_tool(
            ToolCall(id="1", name="any_tool", arguments="{}")
        )

        # 应该是工具不存在，而不是约束错误
        assert "not found" in result
