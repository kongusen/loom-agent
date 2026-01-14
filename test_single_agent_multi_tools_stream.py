"""
测试单Agent多工具模式的流式输出
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

# 流式输出事件监听器
class StreamEventListener:
    """监听并显示流式输出事件"""

    async def on_stream_text(self, event: CloudEvent):
        """处理文本流式输出"""
        text = event.data.get("content", "")
        print(text, end="", flush=True)

    async def on_stream_done(self, event: CloudEvent):
        """处理流式输出结束"""
        print()  # 换行

    async def on_stream_tool_call_start(self, event: CloudEvent):
        """处理工具调用开始"""
        tool_name = event.data.get("tool_name", "")
        print(f"\n🔧 [调用工具: {tool_name}]", flush=True)

    async def on_stream_error(self, event: CloudEvent):
        """处理流式输出错误"""
        error = event.data.get("error", "")
        print(f"\n❌ [错误: {error}]", flush=True)

async def test_single_agent_multi_tools():
    """测试单Agent多工具模式的流式输出"""
    print("=" * 60)
    print("测试: 单Agent多工具模式 - 流式输出")
    print("=" * 60)

    print("\n🔧 创建基础设施...")
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # 创建并注册流式输出监听器（使用通配符订阅）
    listener = StreamEventListener()
    await bus.subscribe("agent.stream.text/*", listener.on_stream_text)
    await bus.subscribe("agent.stream.done/*", listener.on_stream_done)
    await bus.subscribe("agent.stream.tool_call_start/*", listener.on_stream_tool_call_start)
    await bus.subscribe("agent.stream.error/*", listener.on_stream_error)
    print("✅ 流式输出监听器已注册")

    # 创建启用流式输出的OpenAI Provider
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=True
    )
    print(f"✅ Provider创建成功 (stream=True)")

    # 创建多个工具
    def search_web(query: str) -> str:
        """搜索网络信息"""
        return f"搜索结果: 关于'{query}'的最新信息..."

    def calculate(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression)
            return f"计算结果: {expression} = {result}"
        except:
            return f"计算错误: 无法计算 {expression}"

    def get_weather(city: str) -> str:
        """获取天气信息"""
        return f"天气信息: {city}今天晴天，温度25°C"

    def translate_text(text: str, target_lang: str = "en") -> str:
        """翻译文本"""
        return f"翻译结果: '{text}' -> '{target_lang}' language"

    # 创建ToolNode
    search_tool = ToolNode(
        node_id="search-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="search_web",
            description="Search the web for information",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        ),
        func=search_web
    )

    calc_tool = ToolNode(
        node_id="calc-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="calculate",
            description="Calculate mathematical expressions",
            inputSchema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"]
            }
        ),
        func=calculate
    )

    weather_tool = ToolNode(
        node_id="weather-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="get_weather",
            description="Get weather information for a city",
            inputSchema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"]
            }
        ),
        func=get_weather
    )

    translate_tool = ToolNode(
        node_id="translate-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="translate_text",
            description="Translate text to target language",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "target_lang": {"type": "string"}
                },
                "required": ["text"]
            }
        ),
        func=translate_text
    )

    print(f"✅ 创建了4个工具: search_web, calculate, get_weather, translate_text")

    # 创建单Agent配置多工具
    agent = (LoomBuilder()
        .with_id('multi-tool-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([search_tool, calc_tool, weather_tool, translate_tool])
        .with_agent(
            role='Multi-Tool Assistant',
            system_prompt='You are a helpful assistant with multiple tools. Use the appropriate tools to answer user questions.'
        )
        .build())
    print(f"✅ Agent创建成功 (配置了4个工具)")

    # 测试复杂任务，需要使用多个工具
    print(f"\n{'='*60}")
    print(f"📨 发送复杂任务...")
    print(f"{'='*60}")
    print("💭 Agent思考过程（流式显示）:\n")

    event = CloudEvent(
        type="node.request",
        source="user",
        data={
            "content": """Please help me with the following tasks:
1. Calculate: (100 + 50) * 2
2. Get weather for Beijing
3. Search for latest AI news
4. Translate 'Hello World' to Chinese

Use the appropriate tools and provide a summary."""
        }
    )

    result = await agent.process(event)

    print(f"\n\n{'='*60}")
    print(f"🤖 最终响应:")
    print(f"{'='*60}")
    print(result)

    return result

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_single_agent_multi_tools())
    print("\n✅ 单Agent多工具流式输出测试完成\n")
