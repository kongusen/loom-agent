"""
测试流式输出在不同模式下的表现
1. Crew串行模式 - 子agent思考过程流式显示
2. 并行模式 - 结果流式显示
3. ReAct范式 - 整个推理过程流式显示
"""
import asyncio
import os
from loom import LoomBuilder
from loom.llm import OpenAIProvider
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent

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

print("=" * 60)
print("测试1: Crew串行模式 - 流式输出")
print("=" * 60)

async def test_crew_serial_stream():
    """测试Crew串行模式下的流式输出"""
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
        stream=True  # 启用流式输出
    )
    print(f"✅ Provider创建成功 (stream=True)")

    print("\n🔧 创建Crew成员...")
    # Agent 1: Researcher
    researcher = (LoomBuilder()
        .with_id('researcher')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Researcher',
            system_prompt='You are a researcher. Gather information and facts about the topic.'
        )
        .build())
    print(f"✅ Researcher创建成功")

    # Agent 2: Analyst
    analyst = (LoomBuilder()
        .with_id('analyst')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Analyst',
            system_prompt='You are an analyst. Analyze information and draw insights.'
        )
        .build())
    print(f"✅ Analyst创建成功")

    # Agent 3: Writer
    writer = (LoomBuilder()
        .with_id('writer')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Writer',
            system_prompt='You are a writer. Write clear and engaging content.'
        )
        .build())
    print(f"✅ Writer创建成功")

    # 开始串行协作任务
    topic = "AI Agent的未来发展"
    print(f"\n{'='*60}")
    print(f"📋 Crew任务: {topic}")
    print(f"{'='*60}")

    # Step 1: Researcher收集信息
    print(f"\n🔍 [Step 1] Researcher开始收集信息...")
    print("💭 思考过程:")
    research_event = CloudEvent(
        type="node.request",
        source="coordinator",
        data={"content": f"Research the topic: {topic}. Provide key facts."}
    )
    research_result = await researcher.process(research_event)
    print(f"\n✅ Research完成")
    print(f"📄 结果: {research_result[:150]}...")

    # Step 2: Analyst分析信息
    print(f"\n📊 [Step 2] Analyst开始分析...")
    print("💭 思考过程:")
    analysis_event = CloudEvent(
        type="node.request",
        source="coordinator",
        data={"content": f"Analyze this research: {research_result}"}
    )
    analysis_result = await analyst.process(analysis_event)
    print(f"\n✅ Analysis完成")
    print(f"📄 结果: {analysis_result[:150]}...")

    # Step 3: Writer撰写报告
    print(f"\n✍️ [Step 3] Writer开始撰写报告...")
    print("💭 思考过程:")
    writing_event = CloudEvent(
        type="node.request",
        source="coordinator",
        data={"content": f"Write a report based on: {analysis_result}"}
    )
    final_report = await writer.process(writing_event)
    print(f"\n✅ Writing完成")

    print(f"\n{'='*60}")
    print(f"📝 最终报告:")
    print(f"{'='*60}")
    print(final_report)

    return final_report

# 运行测试1
asyncio.run(test_crew_serial_stream())
print("\n✅ 测试1完成\n")

print("=" * 60)
print("测试2: 并行模式 - 流式输出")
print("=" * 60)

async def test_parallel_stream():
    """测试并行模式下的流式输出"""
    from loom.node.tool import ToolNode
    from loom.protocol.mcp import MCPToolDefinition

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
    def get_weather(city: str) -> str:
        return f"Weather in {city}: Sunny, 25°C"

    def get_time(timezone: str) -> str:
        return f"Time in {timezone}: 14:30"

    def get_news(category: str) -> str:
        return f"Latest {category} news: AI advances"

    # 创建ToolNode
    weather_tool = ToolNode(
        node_id="weather-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="get_weather",
            description="Get weather information",
            inputSchema={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        ),
        func=get_weather
    )

    time_tool = ToolNode(
        node_id="time-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="get_time",
            description="Get current time",
            inputSchema={"type": "object", "properties": {"timezone": {"type": "string"}}, "required": ["timezone"]}
        ),
        func=get_time
    )

    news_tool = ToolNode(
        node_id="news-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="get_news",
            description="Get latest news",
            inputSchema={"type": "object", "properties": {"category": {"type": "string"}}, "required": ["category"]}
        ),
        func=get_news
    )
    print(f"✅ 创建了3个工具")

    # 创建支持并行执行的Agent
    agent = (LoomBuilder()
        .with_id('parallel-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([weather_tool, time_tool, news_tool])
        .with_execution(parallel_execution=True, concurrency_limit=3)
        .with_agent(
            role='Information Assistant',
            system_prompt='You are an information assistant. Use tools to gather information.'
        )
        .build())
    print(f"✅ Agent创建成功 (parallel_execution=True)")

    # 测试并行工具调用
    print(f"\n📨 发送问题: 获取北京天气、UTC时间和科技新闻")
    print("💭 Agent思考并并行调用工具...")
    event = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "Please tell me: 1) weather in Beijing, 2) time in UTC, 3) tech news. Use tools."}
    )

    result = await agent.process(event)
    print(f"\n✅ 并行执行完成")
    print(f"\n🤖 最终响应:")
    print(result)

    return result

# 运行测试2
asyncio.run(test_parallel_stream())
print("\n✅ 测试2完成\n")

print("=" * 60)
print("测试3: ReAct范式 - 流式输出")
print("=" * 60)

async def test_react_stream():
    """测试ReAct范式下的流式输出（展示完整推理过程）"""
    from loom.node.tool import ToolNode
    from loom.protocol.mcp import MCPToolDefinition

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

    # 创建计算器工具（用于ReAct推理）
    def calculator(operation: str, a: float, b: float) -> float:
        result = {"add": a + b, "multiply": a * b, "subtract": a - b, "divide": a / b if b != 0 else "Error"}
        return result.get(operation, "Unknown operation")

    calc_tool = ToolNode(
        node_id="calculator-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="calculator",
            description="Perform arithmetic operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["add", "multiply", "subtract", "divide"]},
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["operation", "a", "b"]
            }
        ),
        func=calculator
    )
    print(f"✅ 计算器工具创建成功")

    # 创建Agent（ReAct模式）
    agent = (LoomBuilder()
        .with_id('react-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([calc_tool])
        .with_agent(
            role='Math Assistant',
            system_prompt='You are a math assistant. Think step by step and use the calculator tool when needed.'
        )
        .build())
    print(f"✅ Agent创建成功 (ReAct模式)")

    # 测试ReAct推理过程
    print(f"\n📨 发送问题: 计算 (15 + 25) * 3")
    print("💭 展示完整ReAct推理过程:")
    print("   [Thought → Action → Observation → Thought → ...]")
    event = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "Calculate (15 + 25) * 3. Think step by step and use the calculator tool."}
    )

    result = await agent.process(event)
    print(f"\n✅ ReAct推理完成")
    print(f"\n🤖 最终答案:")
    print(result)

    return result

# 运行测试3
asyncio.run(test_react_stream())
print("\n✅ 测试3完成\n")

print("=" * 60)
print("✅ 所有流式输出测试完成")
print("=" * 60)
