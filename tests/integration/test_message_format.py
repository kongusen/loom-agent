"""
测试消息历史格式是否符合 OpenAI API 要求
"""

import pytest
import asyncio
from loom.node.agent import AgentNode
from loom.node.tool import ToolNode
from loom.api.main import LoomApp
from loom.protocol.cloudevents import CloudEvent
from loom.interfaces.llm import LLMProvider, LLMResponse
from loom.protocol.mcp import MCPToolDefinition as ToolDefinition
from loom.memory.hierarchical import HierarchicalMemory


class MockLLMWithToolCall(LLMProvider):
    """模拟返回工具调用的LLM"""
    def __init__(self):
        self.call_count = 0

    async def chat(self, messages, tools=None):
        self.call_count += 1
        if self.call_count == 1:
            # 第一次调用：返回工具调用（content为空）
            return LLMResponse(
                content="",  # 空内容
                tool_calls=[{
                    "id": "call_123",
                    "name": "test_tool",
                    "arguments": {"query": "test"}
                }]
            )
        else:
            # 第二次调用：返回最终答案
            return LLMResponse(content="Final answer")

    async def stream_chat(self, *args, **kwargs):
        pass


class MockToolNode(ToolNode):
    """模拟工具节点"""
    async def process(self, event: CloudEvent):
        return {"result": "Tool executed successfully"}


@pytest.mark.asyncio
async def test_message_format_with_tool_calls():
    """
    测试消息历史格式：
    1. assistant消息应该包含tool_calls（即使content为空）
    2. tool消息应该包含tool_call_id
    """
    app = LoomApp()

    # 创建工具
    tool_def = ToolDefinition(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object", "properties": {}}
    )
    tool = MockToolNode(
        node_id="test_tool",
        dispatcher=app.dispatcher,
        tool_def=tool_def,
        func=lambda x: "success"
    )

    # 创建内存和agent
    memory = HierarchicalMemory()
    provider = MockLLMWithToolCall()

    agent = AgentNode(
        node_id="test_agent",
        dispatcher=app.dispatcher,
        tools=[tool],
        provider=provider,
        memory=memory
    )

    await asyncio.sleep(0.1)

    # 执行任务
    event = CloudEvent.create(
        source="user",
        type="node.request",
        data={"task": "Test task", "max_iterations": 3},
        subject="node/test_agent"
    )

    result = await agent.process(event)

    # 验证结果
    assert result["response"] == "Final answer"
    assert result["iterations"] == 2

    # 关键验证：检查消息历史格式
    messages = await memory.get_recent(limit=10)

    print("\n=== 消息历史 ===")
    for i, msg in enumerate(messages):
        print(f"{i}: {msg}")

    # 验证消息结构
    assert len(messages) >= 3, "应该至少有3条消息：user, assistant, tool"

    # 找到assistant消息（带tool_calls的）
    assistant_msg = None
    for msg in messages:
        if msg["role"] == "assistant" and "tool_calls" in msg:
            assistant_msg = msg
            break

    assert assistant_msg is not None, "应该有一条assistant消息包含tool_calls"
    assert "tool_calls" in assistant_msg, "assistant消息应该包含tool_calls字段"
    assert len(assistant_msg["tool_calls"]) > 0, "tool_calls不应该为空"
    assert assistant_msg["tool_calls"][0]["id"] == "call_123", "tool_call应该有id"

    # 找到tool消息
    tool_msg = None
    for msg in messages:
        if msg["role"] == "tool":
            tool_msg = msg
            break

    assert tool_msg is not None, "应该有一条tool消息"
    assert "tool_call_id" in tool_msg, "tool消息应该包含tool_call_id字段"
    assert tool_msg["tool_call_id"] == "call_123", "tool_call_id应该匹配"
    assert "name" in tool_msg, "tool消息应该包含name字段"

    print("\n✓ 消息格式验证通过！")
    print(f"✓ Assistant消息包含tool_calls: {assistant_msg['tool_calls']}")
    print(f"✓ Tool消息包含tool_call_id: {tool_msg['tool_call_id']}")


@pytest.mark.asyncio
async def test_message_format_without_tool_calls():
    """
    测试没有工具调用时的消息格式
    """
    app = LoomApp()
    memory = HierarchicalMemory()

    # 创建一个不调用工具的LLM
    class SimpleLLM(LLMProvider):
        async def chat(self, messages, tools=None):
            return LLMResponse(content="Simple answer")
        async def stream_chat(self, *args, **kwargs):
            pass

    agent = AgentNode(
        node_id="simple_agent",
        dispatcher=app.dispatcher,
        provider=SimpleLLM(),
        memory=memory
    )

    await asyncio.sleep(0.1)

    event = CloudEvent.create(
        source="user",
        type="node.request",
        data={"task": "Simple task"},
        subject="node/simple_agent"
    )

    result = await agent.process(event)

    assert result["response"] == "Simple answer"

    # 验证消息历史
    messages = await memory.get_recent(limit=10)

    # 应该有user和assistant消息
    assert len(messages) >= 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Simple answer"

    # assistant消息不应该有tool_calls（因为没有调用工具）
    assert "tool_calls" not in messages[1] or messages[1].get("tool_calls") is None

    print("\n✓ 无工具调用的消息格式验证通过！")
