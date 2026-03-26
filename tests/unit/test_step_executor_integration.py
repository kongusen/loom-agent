"""测试 StepExecutor 在真实循环中的集成"""

import pytest

from loom.agent import Agent
from loom.agent.step_executor import StepExecutor
from loom.config import AgentConfig
from loom.types import ToolCall, ToolContext
from loom.types.scene import ScenePackage
from tests.conftest import MockLLMProvider


class TestStepExecutorIntegration:
    """验证 StepExecutor 在热路径中生效"""

    async def test_constraint_check_blocks_tool(self):
        """验证约束检查可以拦截工具调用"""
        scene = ScenePackage(
            id="no_bash",
            tools=["read_file"],
            constraints={"bash": False}
        )

        agent = Agent(provider=MockLLMProvider([]), config=AgentConfig())
        agent.scene_mgr.register(scene)
        agent.scene_mgr.switch("no_bash")

        # 创建 StepExecutor
        executor = StepExecutor(
            agent=agent,
            tool_registry=agent.tools,
            constraint_validator=agent.constraint_validator,
            resource_guard=agent.resource_guard,
        )

        # 尝试调用被禁用的 bash
        tool_call = ToolCall(id="1", name="bash", arguments='{"command": "ls"}')
        result = await executor.execute_step(tool_call, ToolContext(agent_id=agent.id))

        # 应该被拦截
        assert result.error is not None
        assert not result.is_success

    async def test_resource_quota_blocks_tool(self):
        """验证资源配额可以拦截工具调用"""
        agent = Agent(provider=MockLLMProvider([]), config=AgentConfig())

        # 设置极低配额
        agent.resource_guard._max_tokens = 10
        agent.resource_guard._used_tokens = 15  # 已超配额

        executor = StepExecutor(
            agent=agent,
            tool_registry=agent.tools,
            constraint_validator=agent.constraint_validator,
            resource_guard=agent.resource_guard,
        )

        tool_call = ToolCall(id="1", name="read_file", arguments='{"path": "test.txt"}')
        result = await executor.execute_step(tool_call, ToolContext(agent_id=agent.id))

        # 应该被配额拦截
        assert result.error is not None
        assert "quota" in result.error.lower()

    async def test_execution_trace_recorded(self):
        """验证执行轨迹被正确记录"""
        agent = Agent(provider=MockLLMProvider([]), config=AgentConfig())

        executor = StepExecutor(
            agent=agent,
            tool_registry=agent.tools,
            constraint_validator=agent.constraint_validator,
            resource_guard=agent.resource_guard,
        )

        initial_trace_len = len(agent._execution_trace)

        # 执行一个工具（即使失败也会记录）
        tool_call = ToolCall(id="1", name="nonexistent", arguments='{}')
        await executor.execute_step(tool_call, ToolContext(agent_id=agent.id))

        # 轨迹应该增加
        assert len(agent._execution_trace) > initial_trace_len
