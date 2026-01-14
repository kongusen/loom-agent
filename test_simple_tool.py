"""
简单的工具调用测试
"""
import asyncio
import os
from loom import LoomBuilder
from loom.llm import OpenAIProvider
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition

os.environ["OPENAI_API_KEY"] = "sk-Fy6Y5WV5eugN61DhxH1AjI8th71OWfopqA2OCj5t93UIZ6aF"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "https://xiaoai.plus/v1"

async def main():
    print("🔧 创建基础设施...")
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    print("🔧 创建OpenAI Provider...")
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=False
    )

    print("🔧 创建工具...")
    def add(a: float, b: float) -> float:
        result = a + b
        print(f"   ✅ 工具被调用: add({a}, {b}) = {result}")
        return result

    tool_def = MCPToolDefinition(
        name="add",
        description="Add two numbers",
        inputSchema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }
    )

    tool_node = ToolNode(
        node_id="add-tool",
        dispatcher=dispatcher,
        tool_def=tool_def,
        func=add
    )

    print("🔧 创建Agent...")
    agent = (LoomBuilder()
        .with_id('simple-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([tool_node])
        .with_agent(
            role='Math Assistant',
            system_prompt='You are a math assistant. Use the add tool to calculate sums.'
        )
        .build())

    print(f"✅ Agent创建成功，已注册工具: {list(agent.known_tools.keys())}")

    print("\n📨 发送问题: What is 10 + 25?")

    # 先直接测试LLM响应
    print("\n🔍 直接测试LLM生成的tool_calls:")
    messages = [
        {"role": "system", "content": "You are a math assistant. Use the add tool to calculate sums."},
        {"role": "user", "content": "What is 10 + 25? Use the add tool."}
    ]
    tools_dump = [tool_def.model_dump(by_alias=True)]
    print(f"   发送的工具定义: {tools_dump}")

    llm_resp = await provider.chat(messages, tools=tools_dump)
    print(f"   LLM tool_calls: {llm_resp.tool_calls}")
    print(f"   LLM content: {llm_resp.content}")

    print("\n🔄 通过Agent处理...")
    event = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "What is 10 + 25? Use the add tool."}
    )

    result = await agent.process(event)
    print(f"\n🤖 LLM响应:\n{result}")

asyncio.run(main())
print("\n✅ 测试完成")

