# 基于 Loom 构建完整 Agent 系统指南

本指南将详细介绍如何使用 Loom 框架构建一个包含 Crew、Context、Memory、Skills（工具）和 Node 网络的完整 Agent 系统。

## 目录

1. [系统架构概览](#系统架构概览)
2. [核心概念](#核心概念)
3. [构建步骤](#构建步骤)
4. [实战示例](#实战示例)
5. [最佳实践](#最佳实践)

---

## 系统架构概览

Loom 采用**受控分形架构（Controlled Fractal Architecture）**，所有组件都是节点（Node），支持无限递归组合。

```text
┌─────────────────────────────────────────┐
│           LoomApp (应用入口)            │
│  ┌───────────────────────────────────┐  │
│  │    UniversalEventBus (事件总线)   │  │
│  │    Dispatcher (分发器)            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌───▼───┐   ┌───▼───┐   ┌───▼───┐
    │ Agent │   │ Crew  │   │ Tool  │
    │ Node  │   │ Node  │   │ Node  │
    └───┬───┘   └───┬───┘   └───────┘
        │           │
        │      ┌────┴────┐
        │      │ Agents │
        │      └────────┘
        │
    ┌───▼──────────────┐
    │  Memory System    │
    │  (Metabolic)      │
    └───────────────────┘
```

---

## 核心概念

### 1. Node（节点）- 分形架构的基础

在 Loom 中，**一切都是节点**：

- **AgentNode**: 智能代理节点，拥有记忆和推理能力
- **ToolNode**: 工具节点，封装具体功能
- **CrewNode**: 编排节点，协调多个 Agent
- **RouterNode**: 路由节点，智能分发任务

**分形特性**：复杂的 Agent 集群对外表现为一个简单的节点，可以被其他 Agent 调用。

### 2. Memory（记忆系统）

Loom 提供两种记忆系统：

#### HierarchicalMemory（分层记忆）

- **Ephemeral**: 临时记忆（工具输出）
- **Working**: 工作记忆（最近 N 条）
- **Session**: 会话记忆（完整历史）
- **Long-term**: 长期记忆（向量存储，待实现）

#### MetabolicMemory（新陈代谢记忆）

模拟生物代谢过程：

1. **摄入（Validate）**: 评估信息价值
2. **消化（Sanitize）**: 清洗和压缩上下文
3. **同化（PSO）**: 固化到项目状态对象

### 3. Context（上下文管理）

上下文通过 Memory 系统管理：

- Agent 从 Memory 获取上下文
- Crew 使用 Sanitizer 防止上下文污染
- 支持动态上下文构建和压缩

### 4. Skills/Tools（技能/工具）

基于 **MCP (Model Context Protocol)** 标准：

- 每个工具是一个 `ToolNode`
- Agent 可以拥有多个工具
- 工具定义包含 schema 和实现函数

### 5. Crew（多 Agent 编排）

**重要理解**：CrewNode 是一个**节点**（继承自 Node），但它内部包含**编排规则**和**其他节点的引用**。

- **CrewNode 是节点**：可以被其他节点调用，对外表现为一个节点
- **包含编排规则**：如 `pattern: "sequential"` 定义如何执行
- **引用其他节点**：通过 `agents: List[AgentNode]` 引用已存在的 AgentNode

支持多种编排模式：

- **Sequential**: 顺序执行（A → B → C）
- **Parallel**: 并行执行（待实现）

### 6. Router（智能路由）

**重要理解**：RouterNode（如 AttentionRouter）是一个**节点**（继承自 Node），但它内部包含**路由规则**和**其他节点的引用**。

- **RouterNode 是节点**：可以被其他节点调用，对外表现为一个节点
- **包含路由规则**：如使用 LLM 智能选择目标 Agent
- **引用其他节点**：通过 `agents: List[AgentNode]` 引用已存在的 AgentNode（或 CrewNode）

### 7. Node 网络（拓扑）

基于事件总线架构：

- **UniversalEventBus**: 通用事件总线
- **CloudEvents**: 标准事件协议
- 支持全链路追踪和审计

**分形递归**：节点可以无限嵌套，RouterNode 可以引用 CrewNode，CrewNode 可以引用 AgentNode，AgentNode 可以引用 ToolNode。

---

## 构建步骤

### 步骤 1: 初始化应用

```python
from loom.api.main import LoomApp

# 创建应用实例
app = LoomApp(
    control_config={
        "budget": {"max_tokens": 10000},  # 预算控制
        "depth": {"max_depth": 5},        # 深度控制
        "hitl": ["dangerous.*"]            # 人工介入模式
    }
)

# 启动应用
await app.start()
```

### 步骤 2: 创建工具（Skills）

#### 方法 1: 使用 Factory 辅助函数（推荐）

```python
from loom.api.factory import Tool
from loom.protocol.mcp import MCPToolDefinition

# 定义工具函数
async def calculate(args: dict):
    """计算器工具"""
    expression = args.get("expression", "")
    try:
        result = eval(expression)  # 实际应用中应使用安全的表达式求值
        return {"result": result, "expression": expression}
    except Exception as e:
        return {"error": str(e)}

# 创建工具节点
calculator_tool = Tool(
    app=app,
    name="calculator",
    func=calculate,
    description="执行数学计算",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式"
            }
        },
        "required": ["expression"]
    }
)

app.add_node(calculator_tool)
```

#### 方法 2: 直接创建 ToolNode

```python
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition

# 定义 MCP 工具定义
weather_tool_def = MCPToolDefinition(
    name="get_weather",
    description="获取指定城市的天气信息",
    inputSchema={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称"
            }
        },
        "required": ["city"]
    }
)

# 实现工具函数
async def get_weather(args: dict):
    city = args["city"]
    # 实际应用中调用天气 API
    return f"{city}的天气：晴天，25°C"

# 创建工具节点
weather_tool = ToolNode(
    node_id="tool/weather",
    dispatcher=app.dispatcher,
    tool_def=weather_tool_def,
    func=get_weather
)

app.add_node(weather_tool)
```

### 步骤 3: 配置 Memory（记忆系统）

#### 使用基础分层记忆

```python
from loom.memory.hierarchical import HierarchicalMemory

memory = HierarchicalMemory(
    session_limit=100,    # 会话记忆上限
    working_limit=20      # 工作记忆上限
)
```

#### 使用高级新陈代谢记忆

```python
from loom.builtin.memory.metabolic import MetabolicMemory
from loom.builtin.memory.validators import HeuristicValueAssessor
from loom.builtin.memory.pso import SimplePSO
from loom.builtin.memory.sanitizers import CompressiveSanitizer

memory = MetabolicMemory(
    validator=HeuristicValueAssessor(),  # 价值评估器
    pso=SimplePSO(),                     # 项目状态对象
    sanitizer=CompressiveSanitizer()     # 上下文压缩器
)
```

### 步骤 4: 创建 Agent

#### 基础 Agent

```python
from loom.node.agent import AgentNode
from loom.infra.llm import MockLLMProvider

agent = AgentNode(
    node_id="agent/basic",
    dispatcher=app.dispatcher,
    role="通用助手",
    system_prompt="你是一个乐于助人的 AI 助手。",
    memory=memory  # 使用配置的记忆系统
)

app.add_node(agent)
```

#### 带工具的 Agent

```python
agent_with_tools = AgentNode(
    node_id="agent/assistant",
    dispatcher=app.dispatcher,
    role="智能助手",
    system_prompt="你可以使用计算器和天气工具来帮助用户。",
    tools=[calculator_tool, weather_tool],  # 添加工具
    memory=memory
)

app.add_node(agent_with_tools)
```

#### 使用真实 LLM Provider

```python
from loom.interfaces.llm import LLMProvider, LLMResponse
from typing import List, Dict, Any, AsyncIterator
import openai
import os

class OpenAIProvider(LLMProvider):
    """OpenAI LLM Provider 实现"""
    
    def __init__(self, model: str = "gpt-4"):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
    
    async def chat(
        self, 
        messages: List[Dict[str, Any]], 
        tools=None
    ) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools
        )
        msg = response.choices[0].message
        return LLMResponse(
            content=msg.content,
            tool_calls=[
                t.model_dump() for t in msg.tool_calls
            ] if msg.tool_calls else []
        )
    
    async def stream_chat(self, *args, **kwargs) -> AsyncIterator[str]:
        # 流式响应实现
        yield ""

# 创建使用真实 LLM 的 Agent
real_agent = AgentNode(
    node_id="agent/openai",
    dispatcher=app.dispatcher,
    role="OpenAI 助手",
    provider=OpenAIProvider(model="gpt-4"),
    tools=[calculator_tool, weather_tool],
    memory=memory
)

app.add_node(real_agent)
```

### 步骤 5: 创建 Crew（多 Agent 编排）

#### Sequential（顺序）模式

```python
from loom.node.crew import CrewNode
from loom.builtin.memory.sanitizers import BubbleUpSanitizer

# 创建多个专业 Agent
researcher = AgentNode(
    node_id="agent/researcher",
    dispatcher=app.dispatcher,
    role="研究员",
    system_prompt="你是一个专业的研究员，擅长收集和分析信息。",
    memory=memory
)

writer = AgentNode(
    node_id="agent/writer",
    dispatcher=app.dispatcher,
    role="作家",
    system_prompt="你是一个专业的作家，擅长撰写文章和报告。",
    memory=memory
)

reviewer = AgentNode(
    node_id="agent/reviewer",
    dispatcher=app.dispatcher,
    role="审稿人",
    system_prompt="你是一个专业的审稿人，擅长审查和改进文本。",
    memory=memory
)

app.add_node(researcher)
app.add_node(writer)
app.add_node(reviewer)

# 创建 Crew（顺序执行）
content_crew = CrewNode(
    node_id="crew/content",
    dispatcher=app.dispatcher,
    agents=[researcher, writer, reviewer],
    pattern="sequential",
    sanitizer=BubbleUpSanitizer()  # 上下文清洗器
)

app.add_node(content_crew)
```

### 步骤 6: 创建 Router（智能路由）

```python
from loom.node.router import AttentionRouter

# 创建多个专业 Agent
math_agent = AgentNode(
    node_id="agent/math",
    dispatcher=app.dispatcher,
    role="数学专家",
    system_prompt="你擅长解决数学问题。",
    tools=[calculator_tool],
    memory=memory
)

writing_agent = AgentNode(
    node_id="agent/writing",
    dispatcher=app.dispatcher,
    role="写作专家",
    system_prompt="你擅长写作和文本处理。",
    memory=memory
)

app.add_node(math_agent)
app.add_node(writing_agent)

# 创建智能路由器
router = AttentionRouter(
    node_id="router/main",
    dispatcher=app.dispatcher,
    agents=[math_agent, writing_agent],
    provider=OpenAIProvider()  # 路由器也需要 LLM 来决策
)

app.add_node(router)
```

### 步骤 7: 运行任务

```python
# 运行单个 Agent
result = await app.run(
    task="计算 123 + 456",
    target="agent/assistant"
)
print(result["response"])

# 运行 Crew
crew_result = await app.run(
    task="研究人工智能的最新发展并写一篇报告",
    target="crew/content"
)
print(crew_result["final_output"])

# 运行 Router（自动路由到合适的 Agent）
router_result = await app.run(
    task="帮我解这个方程：x^2 + 5x + 6 = 0",
    target="router/main"
)
print(router_result["result"])
```

---

## 实战示例

### 示例 1: 完整的内容创作系统

```python
import asyncio
from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.node.crew import CrewNode
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition
from loom.memory.hierarchical import HierarchicalMemory
from loom.builtin.memory.sanitizers import BubbleUpSanitizer

async def main():
    # 1. 初始化应用
    app = LoomApp()
    await app.start()
    
    # 2. 创建搜索工具
    async def search_tool(args: dict):
        query = args.get("query", "")
        # 模拟搜索
        return f"搜索结果：关于'{query}'的信息..."
    
    search_tool_def = MCPToolDefinition(
        name="search",
        description="搜索信息",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    )
    
    search_node = ToolNode(
        node_id="tool/search",
        dispatcher=app.dispatcher,
        tool_def=search_tool_def,
        func=search_tool
    )
    app.add_node(search_node)
    
    # 3. 创建记忆系统
    memory = HierarchicalMemory(session_limit=50)
    
    # 4. 创建专业 Agent
    researcher = AgentNode(
        node_id="agent/researcher",
        dispatcher=app.dispatcher,
        role="研究员",
        system_prompt="你是一个专业的研究员，使用搜索工具收集信息。",
        tools=[search_node],
        memory=memory
    )
    
    writer = AgentNode(
        node_id="agent/writer",
        dispatcher=app.dispatcher,
        role="作家",
        system_prompt="你是一个专业的作家，根据研究结果撰写文章。",
        memory=memory
    )
    
    app.add_node(researcher)
    app.add_node(writer)
    
    # 5. 创建 Crew
    crew = CrewNode(
        node_id="crew/content",
        dispatcher=app.dispatcher,
        agents=[researcher, writer],
        pattern="sequential",
        sanitizer=BubbleUpSanitizer()
    )
    app.add_node(crew)
    
    # 6. 运行任务
    result = await app.run(
        task="研究 Python 异步编程并写一篇介绍文章",
        target="crew/content"
    )
    
    print("=== 最终输出 ===")
    print(result["final_output"])
    print("\n=== 执行轨迹 ===")
    for step in result["trace"]:
        print(f"[{step['agent']}]: {step['output'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 2: 带 Router 的智能助手系统

```python
import asyncio
from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.node.router import AttentionRouter
from loom.api.factory import Tool
from loom.memory.hierarchical import HierarchicalMemory

async def main():
    app = LoomApp()
    await app.start()
    
    memory = HierarchicalMemory()
    
    # 创建多个工具
    async def calculator(args: dict):
        expr = args.get("expression", "")
        return {"result": eval(expr)}
    
    calc_tool = Tool(
        app=app,
        name="calculator",
        func=calculator,
        description="执行数学计算"
    )
    app.add_node(calc_tool)
    
    async def translator(args: dict):
        text = args.get("text", "")
        lang = args.get("target_language", "en")
        return f"翻译结果：{text} -> {lang}"
    
    trans_tool = Tool(
        app=app,
        name="translator",
        func=translator,
        description="翻译文本"
    )
    app.add_node(trans_tool)
    
    # 创建专业 Agent
    math_agent = AgentNode(
        node_id="agent/math",
        dispatcher=app.dispatcher,
        role="数学助手",
        tools=[calc_tool],
        memory=memory
    )
    
    lang_agent = AgentNode(
        node_id="agent/language",
        dispatcher=app.dispatcher,
        role="语言助手",
        tools=[trans_tool],
        memory=memory
    )
    
    app.add_node(math_agent)
    app.add_node(lang_agent)
    
    # 创建 Router（需要 LLM Provider）
    from loom.infra.llm import MockLLMProvider
    router = AttentionRouter(
        node_id="router/main",
        dispatcher=app.dispatcher,
        agents=[math_agent, lang_agent],
        provider=MockLLMProvider()
    )
    app.add_node(router)
    
    # 测试路由
    result1 = await app.run("计算 100 * 25", target="router/main")
    print(f"路由结果 1: {result1}")
    
    result2 = await app.run("将'Hello'翻译成中文", target="router/main")
    print(f"路由结果 2: {result2}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 3: 使用 Metabolic Memory 的高级 Agent

```python
import asyncio
from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.builtin.memory.metabolic import MetabolicMemory
from loom.builtin.memory.validators import HeuristicValueAssessor
from loom.builtin.memory.pso import SimplePSO
from loom.builtin.memory.sanitizers import CompressiveSanitizer

async def main():
    app = LoomApp()
    await app.start()
    
    # 创建高级代谢记忆系统
    metabolic_memory = MetabolicMemory(
        validator=HeuristicValueAssessor(),
        pso=SimplePSO(),
        sanitizer=CompressiveSanitizer()
    )
    
    # 创建使用代谢记忆的 Agent
    agent = AgentNode(
        node_id="agent/metabolic",
        dispatcher=app.dispatcher,
        role="智能助手",
        system_prompt="你是一个拥有高级记忆系统的 AI 助手。",
        memory=metabolic_memory
    )
    
    app.add_node(agent)
    
    # 运行多轮对话
    tasks = [
        "我的名字是张三",
        "我喜欢编程",
        "我的职业是什么？",
        "我最喜欢做什么？"
    ]
    
    for task in tasks:
        result = await app.run(task, target="agent/metabolic")
        print(f"Q: {task}")
        print(f"A: {result['response']}\n")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 最佳实践

### 1. Memory 管理

- **短期任务**: 使用 `HierarchicalMemory`，简单高效
- **长期项目**: 使用 `MetabolicMemory`，防止上下文污染
- **定期清理**: 对于长时间运行的 Agent，定期调用 `memory.clear()`

### 2. Crew 设计

- **上下文清洗**: 始终为 Crew 配置 `sanitizer`，防止上下文爆炸
- **Agent 职责**: 每个 Agent 应该有明确的单一职责
- **错误处理**: Crew 中的 Agent 失败时，考虑是否继续执行链

### 3. Tool 设计

- **幂等性**: 工具函数应该是幂等的（相同输入产生相同输出）
- **错误处理**: 工具应该返回结构化的错误信息
- **文档**: 为工具提供清晰的描述和参数说明

### 4. 事件监听和调试

```python
# 监听所有事件
app.on("*", lambda event: print(f"Event: {event.type}"))

# 监听特定事件
app.on("node.error", lambda event: print(f"Error: {event.data}"))

# 监听 Agent 思考过程
app.on("agent.thought", lambda event: print(f"Thought: {event.data}"))
```

### 5. 性能优化

- **并行工具调用**: Agent 可以并行调用多个工具（需要实现）
- **记忆限制**: 合理设置记忆上限，避免内存溢出
- **LLM 缓存**: 对于重复查询，考虑实现响应缓存

### 6. 安全性

- **输入验证**: 工具函数应该验证输入参数
- **权限控制**: 使用 Interceptor 实现权限检查
- **敏感信息**: 不要在日志中输出敏感信息

---

## 总结

Loom 框架提供了构建复杂 Agent 系统的完整工具集：

1. **分形节点架构**: 支持无限递归组合
2. **灵活的记忆系统**: 从简单到高级的多种选择
3. **标准化的工具协议**: 基于 MCP 的工具系统
4. **强大的编排能力**: Crew 和 Router 支持复杂工作流
5. **事件驱动架构**: 基于 CloudEvents 的可观测性

通过本指南，你应该能够：

- ✅ 理解 Loom 的核心概念和架构
- ✅ 创建和配置 Agent、Tool、Crew、Router
- ✅ 选择合适的 Memory 系统
- ✅ 构建完整的 Agent 应用系统
- ✅ 遵循最佳实践进行开发

## 延伸阅读

- [核心概念 - 节点和拓扑](../02_core_concepts/nodes_and_topology.md)
- [核心概念 - 记忆系统](../02_core_concepts/memory_system.md)
- [设计哲学 - 配置即架构](../05_design_philosophy/configuration_as_architecture.md)
- [使用工具指南](./using_tools.md)
- [编排指南](./orchestration.md)
- [API 参考](../07_api_reference/nodes.md)
