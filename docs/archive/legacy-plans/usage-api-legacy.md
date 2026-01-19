# Loom API 设计规范

## 研究总结

### 流行框架的 API 设计模式

#### LangChain
- **createAgent()** - 简单的创建接口
- **LLM + Tools** - 核心组件组合
- **LangGraph** - 图形化状态工作流
- **Middleware** - 扩展和修改行为
- **Memory Management** - 对话能力维护

#### CrewAI
- **Role + Goal + Backstory** - 三要素定义 agent
- **YAML 配置** - 声明式配置支持
- **80/20 规则** - 80% 精力设计任务，20% 定义 agent
- **迭代式开发** - 原型→测试→分析→优化

#### AutoGen
- **分层 API** - Core API + AgentChat API + Extensions API
- **多 Agent 协作** - 对话模式和编排
- **Human-in-the-Loop** - 人机协作集成
- **结构化输出** - JSON 等格式支持
- **Memory 和 Caching** - 上下文维护

### 共同的设计原则

1. **简洁的创建接口** - 一个函数/方法创建 agent
2. **组件化设计** - LLM + Tools + Memory 清晰分离
3. **声明式配置** - 支持配置文件和代码
4. **渐进式复杂度** - 简单用例简单，复杂用例灵活
5. **人机协作** - Human-in-the-Loop 支持
6. **状态管理** - Memory/Context 维护

---

## Loom 框架特性

基于六大公理系统的 AI Agent 框架：

### A1: 统一接口公理
- NodeProtocol、Task、AgentCard
- 标准化的通信协议

### A2: 事件主权公理
- EventBus、SSETransport
- 事件驱动架构

### A3: 分形自相似公理
- FractalOrchestrator、NodeContainer
- 递归的 agent 结构

### A4: 记忆层次公理
- L1-L4 四层记忆系统
- MemoryHierarchy

### A5: 认知调度公理
- RouterOrchestrator、CrewOrchestrator
- 智能任务分发

### A6: 四范式工作公理
- Reflection、ToolUse、Planning、MultiAgent
- 四种工作模式

---

## Loom API 设计原则

### 1. 渐进式复杂度
提供四个层次的 API，满足不同用户需求：
- **Level 1**: 快速开始（一行代码）
- **Level 2**: 标准创建（常用场景）
- **Level 3**: 构建器模式（灵活配置）
- **Level 4**: 完全自定义（高级用户）

### 2. 符合公理
API 设计体现六大公理的理念：
- 使用 AgentCard 声明能力（A1）
- 基于事件驱动（A2）
- 支持分形结构（A3）
- 集成记忆系统（A4）
- 提供编排能力（A5）
- 支持四范式（A6）

### 3. 简洁易用
- 合理的默认值
- 清晰的命名
- 最少的必需参数

### 4. 强大灵活
- 支持自定义组件
- 支持扩展和插件
- 支持高级配置

---

## API 设计方案

### Level 1: 快速开始 API

**目标用户**：初学者、快速原型

**设计**：
```python
from loom import quick_start

# 最简单的方式
agent = quick_start(
    agent_id="my-agent",
    name="My Agent",
    description="A helpful agent"
)

# 带 LLM provider
agent = quick_start(
    agent_id="my-agent",
    name="My Agent",
    llm_provider=provider
)
```

**特点**：
- 一个函数完成所有初始化
- 自动创建所有必需组件
- 提供合理的默认值

### Level 2: 标准创建 API

**目标用户**：常规开发者

**设计**：
```python
from loom import Loom

# 创建 Loom 实例
loom = Loom()

# 创建 agent
agent = loom.create_agent(
    agent_id="my-agent",
    name="My Agent",
    description="A helpful agent",
    capabilities=["tool_use", "reflection"],
    llm_provider=provider,
    tools=tools
)

# 创建多个 agent
agent1 = loom.create_agent(...)
agent2 = loom.create_agent(...)
```

**特点**：
- 清晰的 API 结构
- 支持多 agent 创建
- 共享底层组件

### Level 3: 构建器模式 API

**目标用户**：需要灵活配置的开发者

**设计**：
```python
from loom import LoomBuilder

# 使用 Builder 模式
builder = LoomBuilder()
components = (
    builder
    .with_event_bus()
    .with_dispatcher()
    .with_memory()
    .with_orchestrator("router")
    .build()
)

# 使用组件创建 agent
agent = components.create_agent(...)
```

**特点**：
- 链式调用
- 灵活的组件配置
- 支持自定义组件

### Level 4: 完全自定义 API

**目标用户**：高级用户、框架开发者

**设计**：
```python
# 直接使用底层组件
from loom import EventBus, Dispatcher, MemoryHierarchy
from loom.protocol import AgentCard, Task
from loom.orchestration import RouterOrchestrator

# 手动创建和配置所有组件
bus = EventBus()
dispatcher = Dispatcher(bus)
memory = MemoryHierarchy()
orchestrator = RouterOrchestrator(dispatcher)

# 创建 AgentCard
card = AgentCard(
    agent_id="my-agent",
    name="My Agent",
    description="...",
    capabilities=[...]
)
```

**特点**：
- 完全控制
- 直接访问底层组件
- 适合框架扩展

---

## 下一步

1. 实现 `quick_start()` 函数
2. 实现 `Loom` 类
3. 增强 `LoomBuilder` 类
4. 创建示例和文档
5. 编写测试

---

## 参考资料

- [LangChain API Design](https://langchain.com)
- [CrewAI Documentation](https://crewai.com)
- [Microsoft AutoGen](https://github.com/microsoft/autogen)
