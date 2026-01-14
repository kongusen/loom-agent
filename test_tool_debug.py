"""
调试工具调用问题
"""
import asyncio
import os
from loom import LoomBuilder
from loom.llm import OpenAIProvider
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition

# 设置OpenAI凭证
os.environ["OPENAI_API_KEY"] = "sk-Fy6Y5WV5eugN61DhxH1AjI8th71OWfopqA2OCj5t93UIZ6aF"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "https://xiaoai.plus/v1"

async def test_tool_debug():
    """调试工具调用"""
    # 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # 创建OpenAI Provider
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=False
    )

    # 创建一个简单的工具
    def add_numbers(a: float, b: float) -> float:
        """Add two numbers together"""
        print(f"🔧 Tool被调用: add_numbers({a}, {b})")
        result = a + b
        print(f"🔧 Tool返回: {result}")
        return result

    tool_def = MCPToolDefinition(
        name="add_numbers",
        description="Add two numbers together and return the sum",
        inputSchema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    )

    tool_node = ToolNode(
        node_id="add-tool",
        dispatcher=dispatcher,
        tool_def=tool_def,
        func=add_numbers
    )

    print(f"✅ Tool创建成功: {tool_node.node_id}")
    print(f"   Tool定义: {tool_def.model_dump()}")

    # 创建Agent
    agent = (LoomBuilder()
        .with_id('debug-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([tool_node])
        .with_agent(
            role='Math Assistant',
            system_prompt='You are a math assistant. When asked to add numbers, you MUST use the add_numbers tool.'
        )
        .build())

    print(f"\n✅ Agent创建成功: {agent.node_id}")
    print(f"   已注册工具: {list(agent.known_tools.keys())}")

    # 检查工具定义
    print(f"\n📋 检查Agent的工具注册:")
    print(f"   - known_tools: {agent.known_tools}")
    print(f"   - tool_registry definitions: {[d.name for d in agent.tool_registry.definitions]}")

    # 测试工具调用
    print("\n📨 发送问题: What is 5 + 3? Use the add_numbers tool.")
    event = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "What is 5 + 3? You MUST use the add_numbers tool to calculate this."}
    )

    print("\n🔄 开始处理...")

    # 直接测试LLM是否生成tool_calls
    print("\n🔍 直接测试LLM响应:")
    messages = [
        {"role": "system", "content": agent.system_prompt},
        {"role": "user", "content": "What is 5 + 3? You MUST use the add_numbers tool."}
    ]
    tools = [tool_def.model_dump()]

    llm_response = await provider.chat(messages, tools=tools)
    print(f"   LLM返回类型: {type(llm_response)}")
    print(f"   LLM content: {llm_response.content if hasattr(llm_response, 'content') else llm_response.get('content')}")
    print(f"   LLM tool_calls: {llm_response.tool_calls if hasattr(llm_response, 'tool_calls') else llm_response.get('tool_calls')}")

    print("\n🔄 通过Agent处理...")
    result = await agent.process(event)
    print(f"\n🤖 最终响应:\n{result}")

# 运行测试
asyncio.run(test_tool_debug())
