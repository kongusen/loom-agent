"""
测试工具可选性修复

验证：
1. 传入 tools=[] 时，Agent 不应该有任何工具（包括元工具）
2. 传入 tools=[] 时，Agent 应该能够直接返回 LLM 的文本响应
3. 不传入 tools 参数时，Agent 应该有默认的元工具（保持向后兼容）
"""

import asyncio

from loom.agent.core import Agent
from loom.providers.llm.interface import LLMProvider, StreamChunk


class MockLLMProvider(LLMProvider):
    """模拟 LLM Provider，用于测试"""

    def __init__(self, response_text: str = "这是一个测试响应"):
        self.response_text = response_text

    async def chat(self, messages, **kwargs):
        """同步聊天接口"""
        from types import SimpleNamespace
        return SimpleNamespace(content=self.response_text)

    async def stream_chat(self, messages, **kwargs):
        """流式聊天接口"""
        # 返回文本响应
        yield StreamChunk(type="text", content=self.response_text)


async def test_no_tools_explicit():
    """测试 1: 明确传入 tools=[] 时不应该有任何工具"""
    print("\n=== 测试 1: 明确传入 tools=[] ===")

    llm = MockLLMProvider(response_text='{"result": "success"}')
    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个 JSON 生成器",
        tools=[],  # 明确传入空列表
    )

    # 验证：不应该有任何工具
    print(f"工具数量: {len(agent.all_tools)}")
    print(f"require_done_tool: {agent.require_done_tool}")
    print(f"_user_wants_no_tools: {agent._user_wants_no_tools}")

    if len(agent.all_tools) == 0:
        print("✅ 通过：没有工具被添加")
    else:
        print(f"❌ 失败：仍然有 {len(agent.all_tools)} 个工具")
        print("工具列表:")
        for tool in agent.all_tools:
            if isinstance(tool, dict):
                print(f"  - {tool.get('function', {}).get('name', 'unknown')}")

    if not agent.require_done_tool:
        print("✅ 通过：require_done_tool 已自动禁用")
    else:
        print("❌ 失败：require_done_tool 仍然启用")


async def test_no_tools_response():
    """测试 2: 无工具时应该能够返回 LLM 的文本响应"""
    print("\n=== 测试 2: 无工具时返回文本响应 ===")

    expected_response = "这是一个直接的文本响应，不需要任何工具"
    llm = MockLLMProvider(response_text=expected_response)
    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个助手",
        tools=[],
    )

    # 执行任务
    result = await agent.run("请回答这个问题")

    print(f"返回结果: {result}")

    if result and len(result) > 0:
        print("✅ 通过：成功返回响应")
    else:
        print("❌ 失败：响应为空")


async def test_default_tools():
    """测试 3: 不传入 tools 参数时应该有默认元工具"""
    print("\n=== 测试 3: 默认情况下有元工具（向后兼容）===")

    llm = MockLLMProvider()
    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个助手",
        # 不传入 tools 参数
    )

    print(f"工具数量: {len(agent.all_tools)}")
    print(f"_user_wants_no_tools: {agent._user_wants_no_tools}")

    # 检查是否有元工具
    tool_names = [
        tool.get('function', {}).get('name', '')
        for tool in agent.all_tools
        if isinstance(tool, dict)
    ]

    has_create_plan = 'create_plan' in tool_names
    has_delegate_task = 'delegate_task' in tool_names

    print(f"有 create_plan: {has_create_plan}")
    print(f"有 delegate_task: {has_delegate_task}")

    if has_create_plan and has_delegate_task:
        print("✅ 通过：默认元工具已添加（向后兼容）")
    else:
        print("❌ 失败：缺少默认元工具")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("工具可选性修复测试")
    print("=" * 60)

    await test_no_tools_explicit()
    await test_no_tools_response()
    await test_default_tools()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
