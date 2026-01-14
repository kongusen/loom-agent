"""
使用真实LLM测试Node集群
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

print("=" * 60)
print("测试1: 真实LLM基础对话")
print("=" * 60)

async def test_real_llm_basic():
    """测试使用真实LLM的基础对话"""
    # 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # 创建OpenAI Provider
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=False  # 禁用流式输出，使用标准chat方法
    )

    print(f"✅ OpenAI Provider创建成功")
    print(f"   - Model: {provider.config.generation.model}")
    print(f"   - Base URL: {provider.config.connection.base_url}")

    # 创建Agent
    agent = (LoomBuilder()
        .with_id('real-llm-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='AI Assistant',
            system_prompt='You are a helpful AI assistant. Answer questions concisely and accurately.'
        )
        .build())

    print(f"✅ Agent创建成功: {agent.node_id}")

    # 测试简单对话
    print("\n📨 发送问题: 什么是分型架构？")
    event = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "什么是分型架构？请用一句话简单解释。"}
    )

    result = await agent.process(event)
    print(f"\n🤖 LLM响应:\n{result}")

    return agent

# 运行测试1
agent = asyncio.run(test_real_llm_basic())
print("\n✅ 测试1完成\n")

print("=" * 60)
print("测试2: 真实LLM + Tool调用")
print("=" * 60)

async def test_real_llm_with_tool():
    """测试真实LLM调用工具"""
    from loom.node.tool import ToolNode
    from loom.protocol.mcp import MCPToolDefinition

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

    # 创建计算器工具
    def calculator(operation: str, a: float, b: float) -> float:
        """简单计算器工具"""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            return a / b if b != 0 else "Error: Division by zero"
        return "Unknown operation"

    tool_def = MCPToolDefinition(
        name="calculator",
        description="A calculator that can perform basic arithmetic operations (add, subtract, multiply, divide)",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["operation", "a", "b"]
        }
    )

    tool_node = ToolNode(
        node_id="calculator-tool",
        dispatcher=dispatcher,
        tool_def=tool_def,
        func=calculator
    )

    print(f"✅ Tool创建成功: {tool_node.node_id}")

    # 创建带Tool的Agent
    agent = (LoomBuilder()
        .with_id('tool-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([tool_node])
        .with_agent(
            role='Calculator Assistant',
            system_prompt='You are a helpful calculator assistant. Use the calculator tool to perform calculations.'
        )
        .build())

    print(f"✅ Agent创建成功: {agent.node_id}")
    print(f"   - 已注册工具: {list(agent.known_tools.keys())}")

    # 测试工具调用
    print("\n📨 发送问题: What is 123 multiplied by 456?")
    event = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "What is 123 multiplied by 456? Please use the calculator tool."}
    )

    result = await agent.process(event)
    print(f"\n🤖 LLM响应:\n{result}")

    return agent

# 运行测试2
agent2 = asyncio.run(test_real_llm_with_tool())
print("\n✅ 测试2完成\n")

print("=" * 60)
print("测试3: 真实LLM + 并行工具执行")
print("=" * 60)

async def test_real_llm_parallel_tools():
    """测试真实LLM并行调用多个工具"""
    from loom.node.tool import ToolNode
    from loom.protocol.mcp import MCPToolDefinition

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

    # 创建多个工具
    def get_weather(city: str) -> str:
        """获取天气信息"""
        return f"The weather in {city} is sunny, 25°C"

    def get_time(timezone: str) -> str:
        """获取时间"""
        return f"Current time in {timezone} is 14:30"

    def get_news(category: str) -> str:
        """获取新闻"""
        return f"Latest {category} news: AI technology advances rapidly"

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

    time_tool = ToolNode(
        node_id="time-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="get_time",
            description="Get current time in a timezone",
            inputSchema={
                "type": "object",
                "properties": {"timezone": {"type": "string"}},
                "required": ["timezone"]
            }
        ),
        func=get_time
    )

    news_tool = ToolNode(
        node_id="news-tool",
        dispatcher=dispatcher,
        tool_def=MCPToolDefinition(
            name="get_news",
            description="Get latest news in a category",
            inputSchema={
                "type": "object",
                "properties": {"category": {"type": "string"}},
                "required": ["category"]
            }
        ),
        func=get_news
    )

    print(f"✅ 创建了3个工具: weather, time, news")

    # 创建支持并行执行的Agent
    agent = (LoomBuilder()
        .with_id('parallel-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([weather_tool, time_tool, news_tool])
        .with_execution(parallel_execution=True, max_concurrent=3)
        .with_agent(
            role='Information Assistant',
            system_prompt='You are an information assistant. Use the available tools to gather information.'
        )
        .build())

    print(f"✅ Agent创建成功: {agent.node_id}")
    print(f"   - 已注册工具: {list(agent.known_tools.keys())}")
    print(f"   - 并行执行: {agent.execution_config.parallel_execution}")

    # 测试并行工具调用
    print("\n📨 发送问题: Tell me the weather in Beijing, time in UTC, and tech news")
    event = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "Please tell me: 1) weather in Beijing, 2) current time in UTC timezone, 3) latest tech news. Use the tools to get this information."}
    )

    result = await agent.process(event)
    print(f"\n🤖 LLM响应:\n{result}")

    return agent

# 运行测试3
agent3 = asyncio.run(test_real_llm_parallel_tools())
print("\n✅ 测试3完成\n")

print("=" * 60)
print("测试4: 真实LLM + Crew结构协作")
print("=" * 60)

async def test_real_llm_crew():
    """测试Crew结构的多Agent协作"""
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

    print("🔧 创建Crew成员...")

    # Agent 1: Researcher（研究员）
    researcher = (LoomBuilder()
        .with_id('researcher')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Researcher',
            system_prompt='You are a researcher. Your job is to gather information and facts about the given topic. Be thorough and factual.'
        )
        .build())
    print(f"✅ Researcher创建成功: {researcher.node_id}")

    # Agent 2: Analyst（分析师）
    analyst = (LoomBuilder()
        .with_id('analyst')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Analyst',
            system_prompt='You are an analyst. Your job is to analyze information and draw insights. Be analytical and critical.'
        )
        .build())
    print(f"✅ Analyst创建成功: {analyst.node_id}")

    # Agent 3: Writer（写作者）
    writer = (LoomBuilder()
        .with_id('writer')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Writer',
            system_prompt='You are a writer. Your job is to write clear and engaging content based on research and analysis. Be concise and well-structured.'
        )
        .build())
    print(f"✅ Writer创建成功: {writer.node_id}")
    print(f"\n✅ Crew创建完成，共{3}个成员")

    # 开始协作任务
    topic = "AI Agent框架的发展趋势"
    print(f"\n{'='*60}")
    print(f"📋 Crew任务: {topic}")
    print(f"{'='*60}")

    # Step 1: Researcher收集信息
    print(f"\n🔍 [Step 1] Researcher开始收集信息...")
    research_event = CloudEvent(
        type="node.request",
        source="coordinator",
        data={"content": f"Research the topic: {topic}. Provide key facts and trends."}
    )
    research_result = await researcher.process(research_event)
    print(f"✅ Research完成")
    print(f"📄 Research结果:\n{research_result[:200]}...")

    # Step 2: Analyst分析信息
    print(f"\n📊 [Step 2] Analyst开始分析...")
    analysis_event = CloudEvent(
        type="node.request",
        source="coordinator",
        data={"content": f"Analyze this research result and provide insights:\n\n{research_result}"}
    )
    analysis_result = await analyst.process(analysis_event)
    print(f"✅ Analysis完成")
    print(f"📄 Analysis结果:\n{analysis_result[:200]}...")

    # Step 3: Writer撰写报告
    print(f"\n✍️ [Step 3] Writer开始撰写报告...")
    writing_event = CloudEvent(
        type="node.request",
        source="coordinator",
        data={"content": f"Write a concise report based on this analysis:\n\n{analysis_result}"}
    )
    final_report = await writer.process(writing_event)
    print(f"✅ Writing完成")

    print(f"\n{'='*60}")
    print(f"📝 最终报告:")
    print(f"{'='*60}")
    print(final_report)

    return researcher, analyst, writer, final_report

# 运行测试4
crew_result = asyncio.run(test_real_llm_crew())
print("\n✅ 测试4完成\n")

