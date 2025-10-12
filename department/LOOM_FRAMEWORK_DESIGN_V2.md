# Loom Agent Framework - 框架设计文档 v2.0

> **定位**: 一个强大、灵活、可扩展的 Agent 开发框架
> **对标**: LangChain, LlamaIndex, AutoGPT
> **核心理念**: 提供构建块（Building Blocks），而非完整应用

---

## 🎯 1. 框架定位与设计哲学

### 1.1 核心定位

Loom 是一个 **Agent 开发框架**，而非应用：
- ✅ 提供强大的**核心抽象**和**可组合组件**
- ✅ 开发者可以**灵活组装**构建复杂 Agent 应用
- ✅ 支持**插件化扩展**，无需修改框架核心
- ❌ 不是开箱即用的聊天机器人或特定应用

### 1.2 设计哲学

```
┌─────────────────────────────────────────────────────┐
│  Framework Philosophy: "Composable Building Blocks" │
└─────────────────────────────────────────────────────┘

  【低层抽象】              【中层组件】            【高层应用】

  ┌──────────┐           ┌──────────┐           ┌──────────┐
  │  LLM     │           │  Chain   │           │  ChatBot │
  │  Tool    │    ───►   │  Agent   │    ───►   │  Copilot │
  │  Memory  │           │  Router  │           │  AutoGPT │
  └──────────┘           └──────────┘           └──────────┘

   框架提供                 框架提供               开发者构建
   (Interfaces)           (Components)          (Applications)
```

**核心原则**:
1. **最小化假设**: 不假设特定的使用场景
2. **最大化灵活性**: 每个组件都可独立替换
3. **渐进式复杂度**: 简单场景简单用，复杂场景能扩展
4. **插件优先**: 通过插件扩展，而非修改核心

---

## 🏗️ 2. 框架分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Developer Applications                    │
│   (ChatBot, CodeGen, RAG, Multi-Agent System, etc.)        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  High-Level Abstractions                     │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Agent   │  │  Chain   │  │  Router  │  │  Workflow │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Core Components                           │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Executor │  │ Memory   │  │Scheduler │  │EventBus  │   │
│  │ Pipeline │  │ Manager  │  │          │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Base Interfaces                           │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   LLM    │  │   Tool   │  │  Memory  │  │Compressor│   │
│  │Interface │  │Interface │  │ Backend  │  │ Strategy │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Plugin Ecosystem                          │
│                                                              │
│  📦 llm-openai   📦 llm-claude   📦 tool-filesystem         │
│  📦 memory-redis 📦 vector-store  📦 callback-hooks         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧩 3. 核心抽象设计

### 3.1 基础接口层 (Base Interfaces)

```python
# loom/interfaces/llm.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict

class BaseLLM(ABC):
    """LLM 基础接口 - 所有 LLM 提供者必须实现"""

    @abstractmethod
    async def generate(self, messages: List[Dict]) -> str:
        """同步生成"""
        pass

    @abstractmethod
    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """流式生成"""
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict]
    ) -> Dict:
        """带工具调用的生成"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型名称"""
        pass

    @property
    def supports_tools(self) -> bool:
        """是否支持工具调用 (默认False)"""
        return False


# loom/interfaces/tool.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class BaseTool(ABC):
    """工具基础接口"""

    name: str
    description: str
    args_schema: BaseModel  # Pydantic Model

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """执行工具"""
        pass

    @property
    def is_async(self) -> bool:
        """是否异步工具"""
        return True

    @property
    def is_concurrency_safe(self) -> bool:
        """是否并发安全"""
        return True


# loom/interfaces/memory.py
from abc import ABC, abstractmethod
from typing import List, Optional

class BaseMemory(ABC):
    """内存管理接口"""

    @abstractmethod
    async def add_message(self, message: Message) -> None:
        """添加消息"""
        pass

    @abstractmethod
    async def get_messages(
        self,
        limit: Optional[int] = None
    ) -> List[Message]:
        """获取消息历史"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """清空历史"""
        pass

    async def save(self, path: str) -> None:
        """保存到文件 (可选)"""
        pass

    async def load(self, path: str) -> None:
        """从文件加载 (可选)"""
        pass


# loom/interfaces/compressor.py
from abc import ABC, abstractmethod

class BaseCompressor(ABC):
    """上下文压缩接口"""

    @abstractmethod
    async def compress(
        self,
        messages: List[Message]
    ) -> List[Message]:
        """压缩消息列表"""
        pass

    @abstractmethod
    def should_compress(
        self,
        token_count: int,
        max_tokens: int
    ) -> bool:
        """判断是否需要压缩"""
        pass
```

### 3.2 可组合组件层 (Composable Components)

```python
# loom/components/chain.py
from typing import List, Dict, Any

class Chain:
    """链式调用组件 - 最基础的组合单元"""

    def __init__(self, steps: List[Callable]):
        self.steps = steps

    async def run(self, input: Any) -> Any:
        """顺序执行所有步骤"""
        result = input
        for step in self.steps:
            result = await step(result)
        return result

    def __or__(self, other: 'Chain') -> 'Chain':
        """支持 | 操作符组合链"""
        return Chain(self.steps + other.steps)


# loom/components/router.py
class Router:
    """路由组件 - 条件分支"""

    def __init__(self, condition: Callable, routes: Dict[str, Chain]):
        self.condition = condition
        self.routes = routes

    async def run(self, input: Any) -> Any:
        """根据条件选择路由"""
        route_key = await self.condition(input)
        return await self.routes[route_key].run(input)


# loom/components/agent.py
class Agent:
    """Agent 组件 - ReAct 循环"""

    def __init__(
        self,
        llm: BaseLLM,
        tools: List[BaseTool],
        memory: Optional[BaseMemory] = None,
        max_iterations: int = 10
    ):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.memory = memory or InMemoryStorage()
        self.max_iterations = max_iterations
        self.executor = AgentExecutor(
            llm=llm,
            tools=self.tools,
            memory=self.memory
        )

    async def run(self, input: str) -> str:
        """运行 Agent"""
        return await self.executor.execute(input, self.max_iterations)

    async def stream(self, input: str) -> AsyncGenerator:
        """流式运行"""
        async for chunk in self.executor.stream(input):
            yield chunk
```

### 3.3 高级组合模式

```python
# loom/patterns/multi_agent.py
class MultiAgentSystem:
    """多 Agent 协作系统"""

    def __init__(self, agents: Dict[str, Agent], coordinator: BaseLLM):
        self.agents = agents
        self.coordinator = coordinator

    async def run(self, task: str) -> str:
        """协调多个 Agent 完成任务"""
        # 1. 协调器分解任务
        subtasks = await self._decompose_task(task)

        # 2. 分配给不同 Agent
        results = {}
        for subtask in subtasks:
            agent_name = subtask['agent']
            result = await self.agents[agent_name].run(subtask['task'])
            results[agent_name] = result

        # 3. 汇总结果
        return await self._aggregate_results(results)


# loom/patterns/workflow.py
class Workflow:
    """工作流编排"""

    def __init__(self):
        self.graph = {}  # DAG 图结构

    def add_node(self, name: str, component: Any):
        """添加节点"""
        self.graph[name] = {'component': component, 'deps': []}

    def add_edge(self, from_node: str, to_node: str):
        """添加边"""
        self.graph[to_node]['deps'].append(from_node)

    async def run(self, input: Any) -> Any:
        """拓扑排序执行"""
        # 实现 DAG 执行逻辑
        pass
```

---

## 🔌 4. 插件系统设计

### 4.1 插件注册机制

```python
# loom/plugins/registry.py
from typing import Type, Dict

class PluginRegistry:
    """插件注册中心"""

    _llms: Dict[str, Type[BaseLLM]] = {}
    _tools: Dict[str, Type[BaseTool]] = {}
    _memories: Dict[str, Type[BaseMemory]] = {}

    @classmethod
    def register_llm(cls, name: str):
        """注册 LLM 插件"""
        def decorator(llm_class: Type[BaseLLM]):
            cls._llms[name] = llm_class
            return llm_class
        return decorator

    @classmethod
    def get_llm(cls, name: str, **kwargs) -> BaseLLM:
        """获取 LLM 实例"""
        if name not in cls._llms:
            raise ValueError(f"LLM '{name}' not registered")
        return cls._llms[name](**kwargs)


# 使用示例
@PluginRegistry.register_llm("openai")
class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model

    async def generate(self, messages: List[Dict]) -> str:
        # 实现
        pass
```

### 4.2 插件生态

```
loom/
├── loom-core/              # 核心框架
├── loom-llm-openai/        # OpenAI 插件
├── loom-llm-anthropic/     # Anthropic 插件
├── loom-llm-local/         # 本地模型插件
├── loom-tools-web/         # Web 工具集
├── loom-tools-code/        # 代码工具集
├── loom-memory-redis/      # Redis 内存后端
├── loom-memory-postgres/   # PostgreSQL 后端
├── loom-callbacks/         # 回调钩子系统
└── loom-mcp/               # MCP (Model Context Protocol) 适配器 🆕
```

### 4.3 MCP (Model Context Protocol) 支持 🆕

Loom 框架原生支持 **MCP 协议**，可以直接使用整个 MCP 生态系统的工具！

```python
from loom import Agent
from loom.llms import OpenAI
from loom.mcp import MCPToolRegistry

# 1. 自动发现本地 MCP servers (配置在 ~/.loom/mcp.json)
registry = MCPToolRegistry()
await registry.discover_local_servers()

# 2. 加载指定 MCP server 的工具
tools = await registry.load_servers(["filesystem", "github", "postgres"])

# 3. 在 Agent 中使用 MCP 工具
agent = Agent(llm=OpenAI(api_key="..."), tools=tools)

result = await agent.run(
    "Read config.json, query the database, and create a GitHub issue"
)

await registry.close()
```

**MCP 集成优势**:
- 🌍 **即插即用**: 直接访问整个 MCP 工具生态
- 🔒 **安全可控**: 统一的权限和过滤机制
- 🎨 **灵活组合**: Loom 原生工具 + MCP 工具混合使用
- ⚡ **类型安全**: 自动将 JSON Schema 转换为 Pydantic 模型
- 📦 **命名空间**: `server:tool` 格式避免命名冲突

**可用的 MCP Servers**:
- 📁 `@modelcontextprotocol/server-filesystem` - 文件系统操作
- 🐙 `@modelcontextprotocol/server-github` - GitHub 集成
- 🗄️ `@modelcontextprotocol/server-postgres` - PostgreSQL 数据库
- 🌐 `@modelcontextprotocol/server-puppeteer` - Web 浏览器自动化
- 💬 `@modelcontextprotocol/server-slack` - Slack 集成
- ☁️ 以及数百个社区 MCP servers...

详细文档请参考: [LOOM_MCP_INTEGRATION.md](./LOOM_MCP_INTEGRATION.md)

---

## 🎨 5. 开发者体验设计

### 5.1 简单场景 - 零配置快速开始

```python
# 最简单的使用 - 一行代码
from loom import Agent
from loom.llms import OpenAI

agent = Agent(llm=OpenAI(api_key="..."))
result = await agent.run("What is 2+2?")
```

### 5.2 中等场景 - 添加工具

```python
from loom import Agent
from loom.llms import OpenAI
from loom.tools import Calculator, WebSearch

agent = Agent(
    llm=OpenAI(api_key="..."),
    tools=[Calculator(), WebSearch()]
)

result = await agent.run("Search for Python tutorials and calculate 10*5")
```

### 5.3 复杂场景 - 自定义组件

```python
from loom import Agent, Chain, Router
from loom.llms import OpenAI
from loom.memory import RedisMemory
from loom.tools import BaseTool

# 1. 自定义工具
class MyCustomTool(BaseTool):
    name = "my_tool"
    description = "My custom tool"

    async def run(self, arg: str) -> str:
        return f"Processed: {arg}"

# 2. 构建 Agent
agent = Agent(
    llm=OpenAI(api_key="...", model="gpt-4"),
    tools=[MyCustomTool()],
    memory=RedisMemory(url="redis://localhost"),
    max_iterations=20
)

# 3. 链式组合
chain = (
    Chain([preprocess_input])
    | agent
    | Chain([postprocess_output])
)

result = await chain.run("Complex task")
```

### 5.4 专家场景 - Multi-Agent System

```python
from loom import Agent, MultiAgentSystem
from loom.llms import OpenAI, Claude

# 定义专业 Agent
researcher = Agent(
    llm=OpenAI(model="gpt-4"),
    tools=[WebSearch(), FileRead()],
    name="researcher"
)

coder = Agent(
    llm=Claude(model="claude-3-opus"),
    tools=[PythonREPL(), FileWrite()],
    name="coder"
)

reviewer = Agent(
    llm=OpenAI(model="gpt-4"),
    tools=[CodeLinter(), TestRunner()],
    name="reviewer"
)

# 构建多 Agent 系统
system = MultiAgentSystem(
    agents={"researcher": researcher, "coder": coder, "reviewer": reviewer},
    coordinator=OpenAI(model="gpt-4")
)

# 运行
result = await system.run("Build a web scraper for news articles")
```

---

## 🔧 6. 核心功能模块化设计

### 6.1 执行引擎 (Executor)

```python
# loom/core/executor.py
class AgentExecutor:
    """Agent 执行引擎 - 框架核心"""

    def __init__(
        self,
        llm: BaseLLM,
        tools: Dict[str, BaseTool],
        memory: BaseMemory,
        callbacks: Optional[List[BaseCallback]] = None
    ):
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.callbacks = callbacks or []

        # 可插拔的组件
        self.scheduler = Scheduler()
        self.compressor = None  # 可选
        self.permission_manager = None  # 可选

    async def execute(self, input: str, max_iterations: int) -> str:
        """执行 ReAct 循环"""
        # 实现核心循环逻辑
        pass

    def with_compression(self, compressor: BaseCompressor):
        """添加压缩策略"""
        self.compressor = compressor
        return self

    def with_permissions(self, manager: PermissionManager):
        """添加权限管理"""
        self.permission_manager = manager
        return self
```

### 6.2 工具执行管道 (Tool Pipeline)

```python
# loom/core/pipeline.py
class ToolPipeline:
    """工具执行管道 - 6阶段流水线"""

    stages = [
        DiscoverStage(),
        ValidateStage(),
        AuthorizeStage(),
        CancelCheckStage(),
        ExecuteStage(),
        FormatStage()
    ]

    async def run(self, tool_call: ToolCall) -> ToolResult:
        """通过所有阶段执行工具"""
        context = {"tool_call": tool_call}

        for stage in self.stages:
            context = await stage.process(context)
            if context.get("error"):
                return self._handle_error(context)

        return context["result"]

    def add_stage(self, stage: BaseStage, position: int = -1):
        """动态添加阶段"""
        if position == -1:
            self.stages.append(stage)
        else:
            self.stages.insert(position, stage)
```

### 6.3 回调系统 (Callbacks)

```python
# loom/callbacks/base.py
class BaseCallback:
    """回调基类 - 用于监控、日志、追踪"""

    async def on_agent_start(self, input: str):
        """Agent 开始"""
        pass

    async def on_agent_end(self, output: str):
        """Agent 结束"""
        pass

    async def on_tool_start(self, tool_name: str, input: Dict):
        """工具开始执行"""
        pass

    async def on_tool_end(self, tool_name: str, output: Any):
        """工具执行结束"""
        pass

    async def on_llm_start(self, prompts: List[str]):
        """LLM 调用开始"""
        pass

    async def on_llm_end(self, response: str):
        """LLM 调用结束"""
        pass


# 内置回调
class LoggingCallback(BaseCallback):
    """日志回调"""
    async def on_tool_start(self, tool_name: str, input: Dict):
        logger.info(f"Tool {tool_name} started with {input}")


class MetricsCallback(BaseCallback):
    """指标收集回调"""
    async def on_llm_end(self, response: str):
        self.metrics.record_llm_call(tokens=len(response.split()))
```

---

## 📦 7. 包结构与模块划分

```
loom/
├── __init__.py              # 导出核心 API
├── core/                    # 核心引擎
│   ├── executor.py          # Agent 执行器
│   ├── pipeline.py          # 工具管道
│   ├── scheduler.py         # 调度器
│   ├── memory_manager.py    # 内存管理
│   └── event_bus.py         # 事件总线
│
├── interfaces/              # 基础接口
│   ├── llm.py
│   ├── tool.py
│   ├── memory.py
│   └── compressor.py
│
├── components/              # 可组合组件
│   ├── agent.py
│   ├── chain.py
│   ├── router.py
│   └── workflow.py
│
├── patterns/                # 高级模式
│   ├── multi_agent.py
│   ├── rag.py
│   └── react.py
│
├── plugins/                 # 插件系统
│   ├── registry.py
│   └── loader.py
│
├── callbacks/               # 回调系统
│   ├── base.py
│   ├── logging.py
│   └── metrics.py
│
├── utils/                   # 工具函数
│   ├── token_counter.py
│   ├── validator.py
│   └── serializer.py
│
└── builtin/                 # 内置实现
    ├── llms/                # 内置 LLM
    │   ├── openai.py
    │   └── mock.py
    ├── tools/               # 内置工具
    │   ├── calculator.py
    │   ├── web_search.py
    │   └── filesystem.py
    └── memory/              # 内置内存
        ├── in_memory.py
        └── file_based.py
```

---

## 🚀 8. 框架使用示例

### 8.1 快速开始

```python
# example_01_quickstart.py
from loom import Agent
from loom.llms import OpenAI

# 1. 创建 Agent
agent = Agent(llm=OpenAI(api_key="sk-..."))

# 2. 运行
result = await agent.run("Tell me a joke")
print(result)
```

### 8.2 添加自定义工具

```python
# example_02_custom_tool.py
from loom import Agent
from loom.llms import OpenAI
from loom.tools import BaseTool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    city: str = Field(description="City name")

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather for a city"
    args_schema = WeatherInput

    async def run(self, city: str) -> str:
        # 调用天气 API
        return f"Weather in {city}: Sunny, 25°C"

agent = Agent(
    llm=OpenAI(api_key="..."),
    tools=[WeatherTool()]
)

result = await agent.run("What's the weather in Tokyo?")
```

### 8.3 构建 RAG 系统

```python
# example_03_rag.py
from loom import Chain, Agent
from loom.llms import OpenAI
from loom.tools import VectorSearch
from loom.patterns import RAGPattern

# 1. 定义 RAG 流程
def retrieve(query: str) -> List[str]:
    return vector_db.search(query, k=5)

def augment(query: str, docs: List[str]) -> str:
    return f"Context: {docs}\n\nQuestion: {query}"

# 2. 构建链
rag_chain = Chain([
    retrieve,
    augment,
    Agent(llm=OpenAI(api_key="..."))
])

# 3. 使用
result = await rag_chain.run("What is Loom?")
```

### 8.4 Multi-Agent 协作

```python
# example_04_multi_agent.py
from loom import Agent, MultiAgentSystem
from loom.llms import OpenAI, Claude

# 定义专业 Agent
planner = Agent(
    llm=OpenAI(model="gpt-4"),
    tools=[],
    system_prompt="You are a task planning expert"
)

executor = Agent(
    llm=Claude(model="claude-3-sonnet"),
    tools=[PythonREPL(), FileSystem()],
    system_prompt="You are a code execution expert"
)

# 构建系统
system = MultiAgentSystem({
    "planner": planner,
    "executor": executor
})

result = await system.run("Build a data analysis script")
```

---

## 🎯 9. 与 LangChain 的对比

| 特性 | Loom | LangChain |
|------|------|-----------|
| **设计理念** | 组合优先，最小化假设 | 功能丰富，开箱即用 |
| **核心抽象** | Agent, Chain, Router | Chain, Agent, Retriever |
| **扩展方式** | 插件注册中心 | 继承基类 |
| **工具执行** | 6阶段流水线 | Toolkit 模式 |
| **内存管理** | 可插拔压缩策略 | ConversationBuffer |
| **并发控制** | 内置调度器 | 需手动实现 |
| **Multi-Agent** | 一等公民支持 | 通过 AutoGPT 扩展 |
| **类型安全** | 强类型 + Pydantic | 部分类型提示 |
| **性能监控** | 内置 Metrics + Callbacks | 需第三方集成 |

**Loom 的优势**:
- ✅ 更清晰的抽象层次
- ✅ 更强的类型安全
- ✅ 更灵活的组合模式
- ✅ 更完善的并发支持
- ✅ 更易于测试和扩展

---

## 🔄 10. 核心设计模式

### 10.1 Pipeline Pattern (流水线模式)

```python
# 工具执行流水线
tool_call → Discover → Validate → Authorize → Execute → Format → Result
```

### 10.2 Chain Pattern (链式模式)

```python
# 链式组合
step1 | step2 | step3
```

### 10.3 Router Pattern (路由模式)

```python
# 条件分支
if condition:
    route_a.run()
else:
    route_b.run()
```

### 10.4 Observer Pattern (观察者模式)

```python
# 回调系统
agent.add_callback(LoggingCallback())
agent.add_callback(MetricsCallback())
```

### 10.5 Strategy Pattern (策略模式)

```python
# 压缩策略
agent.with_compression(StructuredCompressor())
# or
agent.with_compression(SlidingWindowCompressor())
```

---

## 📝 11. 开发者 API 设计

### 11.1 核心 API

```python
# loom/__init__.py
from loom.components import Agent, Chain, Router, Workflow
from loom.patterns import MultiAgentSystem, RAGPattern
from loom.callbacks import LoggingCallback, MetricsCallback

__all__ = [
    # Core Components
    "Agent",
    "Chain",
    "Router",
    "Workflow",

    # Patterns
    "MultiAgentSystem",
    "RAGPattern",

    # Callbacks
    "LoggingCallback",
    "MetricsCallback",
]
```

### 11.2 插件 API

```python
# loom.llms (官方 LLM 插件)
from loom.llms import OpenAI, Anthropic, HuggingFace

# loom.tools (官方工具插件)
from loom.tools import (
    Calculator,
    WebSearch,
    FileSystem,
    PythonREPL,
    SQLDatabase
)

# loom.memory (官方内存插件)
from loom.memory import (
    InMemory,
    Redis,
    PostgreSQL,
    FileSystem
)
```

### 11.3 配置 API

```python
# loom.config
from loom import config

config.set_default_llm(OpenAI(api_key="..."))
config.set_default_memory(Redis(url="..."))
config.set_max_iterations(50)
config.enable_metrics(True)
```

---

## 🧪 12. 测试友好设计

### 12.1 Mock LLM

```python
from loom.testing import MockLLM

# 测试时使用 Mock
mock_llm = MockLLM(responses=[
    "I will use the calculator tool",
    "The answer is 4"
])

agent = Agent(llm=mock_llm, tools=[Calculator()])
result = await agent.run("What is 2+2?")
assert "4" in result
```

### 12.2 测试工具

```python
from loom.testing import AgentTester

tester = AgentTester(agent)
tester.expect_tool_call("calculator", args={"expression": "2+2"})
tester.expect_final_answer(contains="4")

await tester.run("What is 2+2?")
tester.assert_expectations()
```

---

## 📚 13. 文档结构

```
docs/
├── quickstart/
│   ├── installation.md
│   ├── first_agent.md
│   └── adding_tools.md
│
├── concepts/
│   ├── agents.md
│   ├── chains.md
│   ├── tools.md
│   └── memory.md
│
├── guides/
│   ├── custom_tools.md
│   ├── custom_llm.md
│   ├── multi_agent.md
│   └── rag_pattern.md
│
├── api/
│   ├── core.md
│   ├── components.md
│   └── plugins.md
│
└── examples/
    ├── chatbot.md
    ├── code_assistant.md
    └── research_agent.md
```

---

## 🎯 14. 总结

### 14.1 框架核心价值

1. **极致的灵活性**: 每个组件都可独立替换
2. **渐进式复杂度**: 简单场景简单用，复杂场景能扩展
3. **类型安全**: 基于 Pydantic 的强类型系统
4. **插件生态**: 官方 + 社区插件丰富扩展
5. **测试友好**: 完善的 Mock 和测试工具

### 14.2 开发者体验

```python
# 简单
agent = Agent(llm=OpenAI(api_key="..."))
await agent.run("Hello")

# 强大
system = MultiAgentSystem({...})
result = await system.run("Complex task")
```

### 14.3 下一步

- ✅ **Phase 1**: 实现核心接口和基础组件
- ✅ **Phase 2**: 构建官方插件生态
- ✅ **Phase 3**: 完善文档和示例
- ✅ **Phase 4**: 社区驱动的插件市场

---

**Loom: Build Intelligent Agents with Building Blocks 🧩**
