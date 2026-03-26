"""测试 P0 Harness 约束系统优化."""

import time

import pytest

from loom.agent import Agent, ConstraintValidator, ResourceGuard
from loom.config import AgentConfig
from loom.scene import SceneManager
from loom.types import CompletionParams, CompletionResult, FinishReason, LLMProvider, ToolCall
from loom.types.scene import ScenePackage


class MockProvider(LLMProvider):
    async def complete(self, params: CompletionParams) -> CompletionResult:
        return CompletionResult(
            content="Task completed.",
            finish_reason=FinishReason.STOP,
            tool_calls=[],
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

    async def stream(self, params: CompletionParams):
        yield {"type": "text", "text": "Mock"}


# ── ConstraintValidator 测试 ──


def test_constraint_validator_whitelist():
    """测试工具白名单验证."""
    scene_mgr = SceneManager()
    scene = ScenePackage(
        id="restricted",
        tools=["bash", "read_file"],
        constraints={"network": False},
    )
    scene_mgr.register(scene)
    scene_mgr.switch("restricted")

    validator = ConstraintValidator(scene_mgr)

    # 允许的工具
    valid, msg = validator.validate_before_call(ToolCall(id="1", name="bash", arguments="{}"))
    assert valid
    assert msg == ""

    # 不在白名单的工具
    valid, msg = validator.validate_before_call(ToolCall(id="2", name="web_search", arguments="{}"))
    assert not valid
    assert "not allowed" in msg


def test_constraint_validator_network():
    """测试网络约束."""
    scene_mgr = SceneManager()
    scene = ScenePackage(
        id="offline",
        tools=["bash", "web_search"],
        constraints={"network": False},
    )
    scene_mgr.register(scene)
    scene_mgr.switch("offline")

    validator = ConstraintValidator(scene_mgr)

    # 网络工具应该被拦截
    valid, msg = validator.validate_before_call(ToolCall(id="1", name="web_search", arguments="{}"))
    assert not valid
    assert "Network access disabled" in msg


def test_constraint_validator_write():
    """测试写入约束."""
    scene_mgr = SceneManager()
    scene = ScenePackage(
        id="readonly",
        tools=["read_file", "write_file"],
        constraints={"write": False},
    )
    scene_mgr.register(scene)
    scene_mgr.switch("readonly")

    validator = ConstraintValidator(scene_mgr)

    # 写入工具应该被拦截
    valid, msg = validator.validate_before_call(ToolCall(id="1", name="write_file", arguments="{}"))
    assert not valid
    assert "Write access disabled" in msg


def test_constraint_validator_violations():
    """测试违规记录."""
    scene_mgr = SceneManager()
    scene = ScenePackage(id="test", tools=["bash"], constraints={"network": False})
    scene_mgr.register(scene)
    scene_mgr.switch("test")

    validator = ConstraintValidator(scene_mgr)

    # 触发违规
    validator.validate_before_call(ToolCall(id="1", name="web_search", arguments="{}"))

    violations = validator.get_violations()
    assert len(violations) == 1
    assert violations[0]["tool"] == "web_search"
    assert violations[0]["constraint"] == "whitelist"


# ── ResourceGuard 测试 ──


def test_resource_guard_token_quota():
    """测试 Token 配额."""
    guard = ResourceGuard(max_tokens=100, max_time_sec=300)
    guard.start()

    # 在配额内
    within, msg = guard.check_quota(50)
    assert within
    guard.consume(50)

    # 超配额
    within, msg = guard.check_quota(60)
    assert not within
    assert "Token quota exceeded" in msg


def test_resource_guard_time_quota():
    """测试时间配额."""
    guard = ResourceGuard(max_tokens=10000, max_time_sec=1)
    guard.start()

    # 等待超时
    time.sleep(1.1)

    within, msg = guard.check_quota()
    assert not within
    assert "Time quota exceeded" in msg


def test_resource_guard_remaining():
    """测试剩余资源查询."""
    guard = ResourceGuard(max_tokens=100, max_time_sec=10)
    guard.start()

    guard.consume(30)
    assert guard.get_remaining_tokens() == 70

    remaining_time = guard.get_remaining_time()
    assert 9 <= remaining_time <= 10


# ── Agent 集成测试 ──


@pytest.mark.asyncio
async def test_agent_constraint_integration():
    """测试 Agent 集成约束验证."""
    config = AgentConfig(system_prompt="Test", max_steps=3, stream=False)
    agent = Agent(provider=MockProvider(), config=config)

    # 设置受限场景
    scene = ScenePackage(id="restricted", tools=[], constraints={"network": False})
    agent.scene_mgr.register(scene)
    agent.scene_mgr.switch("restricted")

    # 模拟工具调用
    result = await agent._execute_tool(ToolCall(id="1", name="web_search", arguments="{}"))
    assert "Error" in result
    assert "not allowed" in result


@pytest.mark.asyncio
async def test_agent_resource_guard_integration():
    """测试 Agent 集成资源守卫."""
    from loom.tools import ToolRegistry, define_tool
    from pydantic import BaseModel

    class DummyParams(BaseModel):
        pass

    async def dummy_fn(params: DummyParams, ctx) -> str:
        return "done"

    tools = ToolRegistry()
    tools.register(define_tool("dummy", "Dummy tool", DummyParams, dummy_fn))

    config = AgentConfig(system_prompt="Test", max_steps=3, max_tokens=100)
    agent = Agent(provider=MockProvider(), config=config, tools=tools)

    # 启动守卫并消耗超过配额
    agent.resource_guard.start()
    agent.resource_guard.consume(101)  # 超过 100 的限制

    # 超配额应该被拦截
    result = await agent._execute_tool(ToolCall(id="1", name="dummy", arguments="{}"))
    assert "Error" in result
    assert "quota exceeded" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
