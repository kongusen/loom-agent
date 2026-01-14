"""
测试Node集群的各种组合类型
"""
import asyncio
from loom import LoomBuilder
from loom.llm import MockLLMProvider
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition

print("=" * 60)
print("测试1: 单个Agent节点基础功能")
print("=" * 60)

async def test_single_agent():
    """测试单个Agent节点"""
    # 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # 创建MockLLM
    provider = MockLLMProvider()

    # 创建Agent
    agent = (LoomBuilder()
        .with_id('agent-1')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(role='Assistant', system_prompt='You are a helpful assistant.')
        .build())

    print(f"✅ Agent创建成功: {agent.node_id}")
    print(f"   - Role: {agent.role}")
    print(f"   - Memory: {type(agent.memory).__name__}")
    print(f"   - Context: {type(agent.context).__name__}")

    # 测试处理简单请求
    event = CloudEvent(
        type="node.request",
        source="test",
        data={"content": "Hello, what is 2+2?"}
    )

    result = await agent.process(event)
    print(f"✅ Agent响应: {result}")

    return agent

# 运行测试1
agent = asyncio.run(test_single_agent())
print("\n✅ 测试1完成\n")

print("=" * 60)
print("测试2: Agent + Tool节点组合")
print("=" * 60)

async def test_agent_with_tool():
    """测试Agent + Tool组合"""
    # 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    provider = MockLLMProvider()

    # 创建一个简单的Tool
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

    # 创建Tool定义
    tool_def = MCPToolDefinition(
        name="calculator",
        description="A simple calculator that can perform basic arithmetic operations",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["operation", "a", "b"]
        }
    )

    # 创建ToolNode
    tool_node = ToolNode(
        node_id="calculator-tool",
        dispatcher=dispatcher,
        tool_def=tool_def,
        func=calculator
    )

    print(f"✅ Tool创建成功: {tool_node.node_id}")
    print(f"   - Tool名称: {tool_node.tool_def.name}")

    # 创建带Tool的Agent
    agent = (LoomBuilder()
        .with_id('agent-2')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([tool_node])
        .with_agent(role='Calculator Assistant', system_prompt='You are a calculator assistant.')
        .build())

    print(f"✅ Agent创建成功: {agent.node_id}")
    print(f"   - 已注册工具数量: {len(agent.known_tools)}")
    print(f"   - 工具列表: {list(agent.known_tools.keys())}")

    return agent, tool_node

# 运行测试2
agent2, tool = asyncio.run(test_agent_with_tool())
print("\n✅ 测试2完成\n")

print("=" * 60)
print("测试3: 多个Agent协作")
print("=" * 60)

async def test_multi_agent_collaboration():
    """测试多个Agent之间的协作"""
    # 创建共享的基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    provider = MockLLMProvider()

    # 创建Agent 1: 研究员
    researcher = (LoomBuilder()
        .with_id('researcher')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(role='Researcher', system_prompt='You are a researcher who gathers information.')
        .build())

    # 创建Agent 2: 分析师
    analyst = (LoomBuilder()
        .with_id('analyst')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(role='Analyst', system_prompt='You are an analyst who analyzes data.')
        .build())

    # 创建Agent 3: 协调者
    coordinator = (LoomBuilder()
        .with_id('coordinator')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(role='Coordinator', system_prompt='You are a coordinator who manages tasks.')
        .build())

    print(f"✅ 创建了3个Agent:")
    print(f"   - {researcher.node_id} ({researcher.role})")
    print(f"   - {analyst.node_id} ({analyst.role})")
    print(f"   - {coordinator.node_id} ({coordinator.role})")

    # 测试Agent之间的通信
    print("\n📨 测试Agent之间的通信...")

    # Coordinator发送任务给Researcher
    task_event = CloudEvent(
        type="node.request",
        source=coordinator.source_uri,
        data={"content": "Research the topic of AI"}
    )

    result = await researcher.process(task_event)
    print(f"✅ Researcher响应: {result}")

    return researcher, analyst, coordinator

# 运行测试3
agents = asyncio.run(test_multi_agent_collaboration())
print("\n✅ 测试3完成\n")

print("=" * 60)
print("测试4: 分型结构（Fractal Agent）")
print("=" * 60)

async def test_fractal_agent():
    """测试分型Agent（可以创建子Agent）"""
    from loom.config.fractal import FractalConfig

    # 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    provider = MockLLMProvider()

    # 创建支持分型的Agent
    fractal_config = FractalConfig(
        enabled=True,
        max_depth=3,
        enable_explicit_delegation=True,
        synthesis_model="lightweight"
    )

    parent_agent = (LoomBuilder()
        .with_id('parent-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(role='Parent Coordinator', system_prompt='You are a parent agent that can delegate tasks.')
        .with_fractal(
            enabled=True,
            max_depth=3,
            enable_explicit_delegation=True,
            synthesis_model="lightweight"
        )
        .build())

    print(f"✅ 分型Agent创建成功: {parent_agent.node_id}")
    print(f"   - Role: {parent_agent.role}")
    print(f"   - Fractal配置: {parent_agent.get_fractal_config()}")
    print(f"   - 支持显式委托: {parent_agent.get_fractal_config().enable_explicit_delegation if parent_agent.get_fractal_config() else False}")
    print(f"   - 最大深度: {parent_agent.get_fractal_config().max_depth if parent_agent.get_fractal_config() else 'N/A'}")

    # 检查是否有orchestrator和synthesizer
    has_orchestrator = hasattr(parent_agent, 'orchestrator') and parent_agent.orchestrator is not None
    has_synthesizer = hasattr(parent_agent, 'synthesizer') and parent_agent.synthesizer is not None

    print(f"   - Orchestrator: {'✅ 已配置' if has_orchestrator else '❌ 未配置'}")
    print(f"   - Synthesizer: {'✅ 已配置' if has_synthesizer else '❌ 未配置'}")

    return parent_agent

# 运行测试4
fractal_agent = asyncio.run(test_fractal_agent())
print("\n✅ 测试4完成\n")

print("=" * 60)
print("测试5: 复杂工具链（多工具协同）")
print("=" * 60)

async def test_complex_tool_chain():
    """测试Agent使用多个工具协同工作"""
    # 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    provider = MockLLMProvider()

    # 创建多个工具
    # 工具1: 数据获取
    def fetch_data(query: str) -> str:
        """获取数据"""
        return f"Data for '{query}': [1, 2, 3, 4, 5]"

    fetch_tool_def = MCPToolDefinition(
        name="fetch_data",
        description="Fetch data based on query",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    )

    fetch_tool = ToolNode(
        node_id="fetch-tool",
        dispatcher=dispatcher,
        tool_def=fetch_tool_def,
        func=fetch_data
    )

    # 工具2: 数据处理
    def process_data(data: str, operation: str) -> str:
        """处理数据"""
        return f"Processed {data} with {operation}"

    process_tool_def = MCPToolDefinition(
        name="process_data",
        description="Process data with specified operation",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {"type": "string"},
                "operation": {"type": "string"}
            },
            "required": ["data", "operation"]
        }
    )

    process_tool = ToolNode(
        node_id="process-tool",
        dispatcher=dispatcher,
        tool_def=process_tool_def,
        func=process_data
    )

    # 工具3: 数据存储
    def save_data(data: str, location: str) -> str:
        """保存数据"""
        return f"Saved '{data}' to {location}"

    save_tool_def = MCPToolDefinition(
        name="save_data",
        description="Save data to specified location",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {"type": "string"},
                "location": {"type": "string"}
            },
            "required": ["data", "location"]
        }
    )

    save_tool = ToolNode(
        node_id="save-tool",
        dispatcher=dispatcher,
        tool_def=save_tool_def,
        func=save_data
    )

    # 创建带多个工具的Agent
    agent = (LoomBuilder()
        .with_id('multi-tool-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([fetch_tool, process_tool, save_tool])
        .with_agent(role='Data Pipeline Agent', system_prompt='You manage data pipelines.')
        .build())

    print(f"✅ 多工具Agent创建成功: {agent.node_id}")
    print(f"   - 已注册工具数量: {len(agent.known_tools)}")
    print(f"   - 工具列表:")
    for tool_name in agent.known_tools.keys():
        print(f"     • {tool_name}")

    return agent, [fetch_tool, process_tool, save_tool]

# 运行测试5
multi_tool_agent, tools = asyncio.run(test_complex_tool_chain())
print("\n✅ 测试5完成\n")

print("=" * 60)
print("测试6: 并行执行（Parallel Execution）")
print("=" * 60)

async def test_parallel_execution():
    """测试并行执行配置"""
    from loom.config.execution import ExecutionConfig

    # 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    provider = MockLLMProvider()

    # 创建支持并行执行的Agent
    agent = (LoomBuilder()
        .with_id('parallel-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(role='Parallel Executor', system_prompt='You execute tasks in parallel.')
        .with_execution(parallel_execution=True, max_concurrent=5)
        .build())

    print(f"✅ 并行执行Agent创建成功: {agent.node_id}")
    print(f"   - Role: {agent.role}")
    print(f"   - 执行配置:")
    print(f"     • 并行执行: {agent.execution_config.parallel_execution}")
    print(f"     • 最大并发: {agent.execution_config.concurrency_limit}")
    print(f"     • 超时时间: {agent.execution_config.timeout}秒")

    # 检查ToolExecutor
    print(f"   - ToolExecutor: {type(agent.executor).__name__}")

    return agent

# 运行测试6
parallel_agent = asyncio.run(test_parallel_execution())
print("\n✅ 测试6完成\n")

print("=" * 60)
print("测试7: 分型委托实战（Delegation in Action）")
print("=" * 60)

async def test_fractal_delegation():
    """测试分型Agent的实际委托功能"""
    # 创建基础设施
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    provider = MockLLMProvider()

    # 创建支持分型委托的Parent Agent
    parent = (LoomBuilder()
        .with_id('parent-delegator')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(role='Parent Delegator', system_prompt='You delegate complex tasks to child agents.')
        .with_fractal(
            enabled=True,
            max_depth=3,
            enable_explicit_delegation=True,
            synthesis_model="lightweight"
        )
        .build())

    print(f"✅ Parent Agent创建成功: {parent.node_id}")
    print(f"   - 支持分型委托: {parent.get_fractal_config().enable_explicit_delegation}")

    # 检查delegate_subtasks工具是否已注册
    tool_names = [d.name for d in parent.tool_registry.definitions]
    has_delegate_tool = 'delegate_subtasks' in tool_names
    print(f"   - delegate_subtasks工具: {'✅ 已注册' if has_delegate_tool else '❌ 未注册'}")

    if tool_names:
        print(f"   - 内部工具列表:")
        for tool_name in tool_names:
            print(f"     • {tool_name}")

    # 检查orchestrator和synthesizer
    print(f"   - Orchestrator: {'✅' if parent.orchestrator else '❌'}")
    print(f"   - Synthesizer: {'✅' if parent.synthesizer else '❌'}")

    return parent

# 运行测试7
delegator = asyncio.run(test_fractal_delegation())
print("\n✅ 测试7完成\n")

print("=" * 60)
print("🎉 所有测试完成！")
print("=" * 60)
