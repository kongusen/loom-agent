# 🧵 Loom Agent

<div align="center">

**基于递归状态机的生产级 AI Agent 框架**

**Message-Driven Architecture | Type-Safe | Production-Ready**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-65%20passed-brightgreen.svg)]()

**中文** | [English](README_EN.md)

[快速开始](#-快速开始) | [核心架构](#-核心架构三层设计) | [为什么选择 Loom](#-为什么选择-loom-agent) | [文档](#-文档)

</div>

---

## 🎯 什么是 Loom Agent？

Loom Agent 是一个**类型安全、生产就绪**的 AI Agent 框架，基于**递归状态机 + 不可变消息**架构，提供从原型到生产的完整解决方案。

### 🏗️ 核心架构：三层设计

```
┌─────────────────────────────────────────────────────────┐
│  Pattern Layer - 模式层                                  │
│  • Crew（多智能体协作）• Skills（渐进式披露）             │
│  • ReActAgent（推理+行动）• 自定义模式                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Execution Layer - 执行层                                │
│  • AgentExecutor（递归引擎）• Tools（并行执行）           │
│  • HierarchicalMemory（4层记忆+RAG）• Context（智能组装） │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Core Layer - 核心层                                     │
│  • Message（不可变+类型安全）• Event Sourcing（完整追踪） │
│  • Protocol-based Integration（零耦合）                  │
└─────────────────────────────────────────────────────────┘
```

**设计哲学**：

1. **Core Layer**：Message 作为唯一真相来源 (Single Source of Truth)
   - 不可变数据结构 (`@dataclass(frozen=True)`)
   - 完整的历史链追溯 (`history: List[Message]`)
   - 类型安全的序列化/反序列化 (v0.1.9 零数据丢失)

2. **Execution Layer**：智能执行引擎
   - 递归状态机 (`Message → Message`)
   - 工具并行执行 (3x 性能提升)
   - 分层记忆系统 (Ephemeral → Working → Session → Long-term)
   - 智能上下文组装 (token 预算管理)

3. **Pattern Layer**：高级抽象模式
   - Crew 多智能体协作（角色分工、任务委派）
   - Skills 渐进式披露（按需加载，最小化上下文）
   - 开放式扩展（自定义模式）

---

## 🌟 为什么选择 Loom Agent？

### 与其他框架的本质区别

| 维度 | LangGraph | AutoGen | CrewAI | **Loom Agent** |
|------|-----------|---------|--------|----------------|
| **核心抽象** | 图节点 | 会话代理 | 角色配置 | **Message 不可变链** |
| **执行模型** | 图遍历 | 事件循环 | 任务队列 | **递归状态机** |
| **学习曲线** | 陡峭（图语法） | 中等 | 中等 | **平缓（函数式）** |
| **类型安全** | ⚠️ 运行时检查 | ⚠️ 部分 | ❌ 弱类型 | ✅ **编译时+运行时** |
| **数据完整性** | ⚠️ 状态可变 | ⚠️ 状态可变 | ⚠️ 状态可变 | ✅ **不可变架构** |
| **核心依赖** | 10+ 包 | OpenAI 必需 | 5+ 包 | **仅 2 个包** |
| **集成方式** | 内置集成 | 绑定 OpenAI | 内置集成 | **Protocol-based** |
| **Memory 系统** | ❌ 需手动实现 | ⚠️ 基础 | ⚠️ 基础 | ✅ **4层+RAG** |
| **并行执行** | ⚠️ 图级 | ❌ | ❌ | ✅ **工具级+Agent级** |
| **事件追踪** | ⚠️ 基础 | ⚠️ 基础 | ❌ | ✅ **Event Sourcing** |
| **生产就绪** | ⚠️ 需加固 | ⚠️ 需加固 | ⚠️ 需加固 | ✅ **开箱即用** |

### 🎯 Loom Agent 的核心优势

#### 1. 类型安全 + 数据完整性（v0.1.9 重点改进）

```python
# ❌ 其他框架：状态可变，数据丢失风险
state = {"messages": [...], "context": {...}}
state["messages"].append(new_msg)  # 可变，难以追踪
serialized = pickle.dumps(state)   # 序列化后部分数据丢失

# ✅ Loom：不可变 Message，零数据丢失
from loom.core.message import Message, get_message_history

msg = Message(role="user", content="Hello")
msg_with_history = msg.with_history([prev_msg])  # 返回新实例，原实例不变

# 序列化保留完整历史（v0.1.9 新特性）
data = msg_with_history.to_dict(include_history=True)
restored = Message.from_dict(data)  # 完整恢复，包括历史链
```

**解决的问题**：
- ✅ 消息历史完整保留（v0.1.9 修复序列化丢失）
- ✅ 冻结数据类 100% 合规（v0.1.9 消除所有突变）
- ✅ 类型安全的工具结果（v0.1.9 结构化序列化）

#### 2. 递归状态机：极简而强大

```python
# ❌ LangGraph：复杂的图定义
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_edge("agent", "tools")
graph.add_conditional_edges("tools", should_continue, {
    "continue": "agent",
    "end": END
})
app = graph.compile()  # 需要编译

# ✅ Loom：纯函数递归
async def run(self, message: Message) -> Message:
    response = await self.llm.generate([message])
    if response.finish_reason == "stop":
        return response

    # 工具调用 → 递归
    tool_results = await execute_tools(response.tool_calls)
    return await self.run(message.with_tool_results(tool_results))
```

**优势**：
- 🎯 **零学习成本**：普通 Python 函数
- 📊 **执行栈清晰**：调试就像调试普通递归
- 🛡️ **自动循环检测**：内置最大递归深度保护
- 🔧 **易于扩展**：标准 Python async/await

#### 3. HierarchicalMemory：类人记忆架构 + RAG（v0.1.8 引入，v0.1.9 优化）

```python
# ❌ 其他框架：简单列表，无结构
memory = ConversationBufferMemory()  # 只是消息列表
memory.add_message(msg)              # 无层级，无检索

# ✅ Loom：4层记忆 + 语义检索
from loom.builtin.memory import HierarchicalMemory

memory = HierarchicalMemory(
    embedding=openai_embedding,
    enable_smart_promotion=True,        # v0.1.9: 智能晋升
    summarization_llm=llm_mini,         # v0.1.9: LLM 摘要
    enable_async_vectorization=True,    # v0.1.9: 异步向量化
    enable_ephemeral_debug=True,        # v0.1.9: 调试模式
)

# 4层记忆自动管理
await memory.add_message(msg)          # → Session Memory
# 自动提取关键信息 → Working Memory（最近10条）
# Working 满时自动晋升 → Long-term Memory（永久存储+向量化）

# 语义检索
relevant = await memory.retrieve(
    query="用户的编程偏好",
    top_k=5,
    tier="longterm"  # 只搜索长期记忆
)
# 返回: <retrieved_memory><memory tier="longterm" relevance="0.89">...</memory></retrieved_memory>
```

**v0.1.9 新增功能**：
- ✅ **智能晋升**：过滤 trivial 内容（"好的"、"谢谢"），LLM 摘要长文本
- ✅ **异步向量化**：后台任务队列，晋升不阻塞主流程（10x 吞吐量）
- ✅ **调试模式**：Ephemeral Memory 完整状态导出

**解决的问题**：
- 📊 **上下文窗口有限**：自动压缩和检索
- 🧠 **长期记忆**：跨会话知识保留
- 🔍 **语义检索**：找到相关信息而非简单匹配
- ⚡ **性能优化**：异步向量化，不阻塞执行

#### 4. Protocol-based Integration：零耦合

```python
# ❌ 其他框架：绑定特定服务
from autogen import OpenAIAgent  # 必须用 OpenAI

# ✅ Loom：Protocol-based，自由集成
from loom.interfaces.llm import BaseLLM

class MyCustomLLM:
    """实现 BaseLLM Protocol 即可"""
    async def stream(self, messages, tools=None):
        # 你的实现：可以是 OpenAI、Claude、本地模型、自定义 API...
        yield {"type": "content_delta", "content": "..."}
        yield {"type": "tool_calls", "tool_calls": [...]}

# 无缝集成
agent = loom.agent(
    name="agent",
    llm=MyCustomLLM()  # ✅ 任何实现 Protocol 的对象
)
```

**支持的 Protocols**：
- `BaseLLM`: LLM 集成
- `BaseTool`: 工具集成
- `BaseMemory`: 记忆系统集成
- `BaseEmbedding`: 向量化集成
- `BaseVectorStore`: 向量数据库集成

---

## 📦 安装

```bash
# 核心框架（仅 2 个依赖：Python + Pydantic）
pip install loom-agent
```

**要求**: Python 3.11+

**核心依赖**:
- Python >= 3.11
- Pydantic >= 2.5.0

**可选集成**（需要单独安装）：
```bash
# OpenAI 集成
pip install openai

# ChromaDB 向量数据库
pip install chromadb

# FAISS 向量加速
pip install faiss-cpu  # 或 faiss-gpu
```

---

## 🚀 快速开始

### 30秒：最简 Agent

```python
import asyncio
from loom import agent, Message
from examples.integrations.openai_llm import OpenAILLM

async def main():
    # 创建 Agent
    my_agent = agent(
        name="assistant",
        llm=OpenAILLM(api_key="sk-...")
    )

    # 运行
    response = await my_agent.run(
        Message(role="user", content="介绍一下 Loom Agent")
    )
    print(response.content)

asyncio.run(main())
```

### 5分钟：带工具的 Agent

```python
from loom import agent, Message, tool

@tool(name="calculator")
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

@tool(name="search")
async def search(query: str) -> str:
    """搜索信息"""
    # 实际实现：调用搜索 API
    return f"搜索结果：{query}"

my_agent = agent(
    name="assistant",
    llm=OpenAILLM(api_key="sk-..."),
    tools=[calculator, search]
)

response = await my_agent.run(
    Message(role="user", content="搜索 Python 递归，并计算 10 的阶乘")
)
# Agent 自动：
# 1. 调用 search("Python 递归")
# 2. 调用 calculator("factorial(10)")
# 3. 合成最终回答
```

### 10分钟：启用分层记忆 + RAG

```python
from loom import agent, Message
from loom.builtin.memory import HierarchicalMemory
from examples.integrations.openai_llm import OpenAILLM
from examples.integrations.openai_embedding import OpenAIEmbedding

# 创建分层记忆系统
memory = HierarchicalMemory(
    embedding=OpenAIEmbedding(api_key="sk-..."),
    enable_smart_promotion=True,        # 智能晋升
    summarization_llm=OpenAILLM(model="gpt-4o-mini"),  # 轻量级摘要
    enable_async_vectorization=True,    # 异步向量化
)

my_agent = agent(
    name="assistant",
    llm=OpenAILLM(api_key="sk-..."),
    memory=memory,
)

# 第一轮对话
await my_agent.run(Message(role="user", content="我喜欢 Python 和 Rust"))
# → 存入 Session Memory
# → 自动提取到 Working Memory
# → 超过容量后晋升到 Long-term Memory（向量化）

# 第二轮对话（可能在几天后）
response = await my_agent.run(
    Message(role="user", content="推荐一些编程语言")
)
# Agent 自动：
# 1. 从 Long-term Memory 检索 "用户喜欢 Python 和 Rust"
# 2. 结合上下文生成个性化回答
```

---

## ✨ 核心特性详解

### 1. Message 不可变架构（v0.1.9 重点改进）

**问题**：传统框架中状态可变，导致：
- 难以追踪消息流向
- 序列化丢失部分数据
- 并发场景下竞态条件
- 调试困难

**Loom 解决方案**：

```python
from loom.core.message import Message, get_message_history, build_history_chain

# 1. 不可变消息
msg1 = Message(role="user", content="Hello")
msg2 = msg1.reply("Hi there!")  # 返回新消息，msg1 不变

# 2. 历史链追溯
msg3 = msg2.reply("How are you?")
history = get_message_history(msg3)  # [msg1, msg2, msg3]

# 3. 安全的历史构建
new_history = build_history_chain(history, new_msg)  # 不修改原 history

# 4. 完整的序列化（v0.1.9 新特性）
data = msg3.to_dict(include_history=True)  # 包含完整历史链
restored = Message.from_dict(data)         # 零丢失恢复

# 5. 类型安全的工具结果（v0.1.9 新特性）
from loom.core.executor import serialize_tool_result

result = {"data": [1, 2, 3], "status": "ok"}
content, metadata = serialize_tool_result(result)
# content = '{"data": [1, 2, 3], "status": "ok"}'  # 有效 JSON
# metadata = {"content_type": "application/json", "result_type": "dict"}

tool_msg = Message(
    role="tool",
    content=content,
    metadata=metadata  # LLM 可以理解结果类型
)
```

**v0.1.9 改进总结**：
- ✅ `history` 声明为正式 dataclass 字段
- ✅ `get_message_history()` 安全提取函数（类型验证+防御性复制）
- ✅ 修复所有冻结数据类突变
- ✅ 工具结果结构化序列化（保留类型信息）
- ✅ 序列化零数据丢失

### 2. 递归状态机：Agent = Function

**核心思想**：`Agent.run(Message) → Message`

```python
class AgentExecutor:
    async def execute(self, message: Message) -> Message:
        """
        递归执行直到完成

        工作流程：
        1. 检查递归深度
        2. 准备上下文（压缩、记忆增强）
        3. LLM 推理
        4. 工具调用？→ 递归执行
        5. 返回最终结果
        """
        # 1. 检查递归深度
        self.current_depth += 1
        if self.current_depth > self.max_recursion_depth:
            raise RecursionError(f"超过最大递归深度 {self.max_recursion_depth}")

        # 2. 上下文准备
        prepared = await self.context_manager.prepare(message)

        # 3. LLM 推理
        response = await self.llm.stream(messages=prepared)

        # 4. 工具调用？
        if response.tool_calls:
            # 并行执行所有工具
            results = await asyncio.gather(*[
                self.execute_tool(tc) for tc in response.tool_calls
            ])

            # 构建新消息（包含工具结果）
            new_message = build_tool_results_message(message, response, results)

            # 🔥 递归！
            return await self.execute(new_message)

        # 5. 完成
        return response
```

**优势**：
- 🎯 **简单**：就是一个递归函数
- 📊 **可观测**：每一步都有事件
- 🛡️ **安全**：自动循环检测
- 🐛 **易调试**：标准 Python 调试工具

### 3. HierarchicalMemory：4层记忆系统

```
┌─────────────────────────────────────────────┐
│  Ephemeral Memory (工具临时状态)             │
│  用完即弃，不污染对话历史                     │
│  例如：tool_call_123 → "Calling API..."     │
└─────────────────────────────────────────────┘
               ↓ (extract key info)
┌─────────────────────────────────────────────┐
│  Working Memory (最近10条)                   │
│  当前对话的短期焦点                           │
│  例如：最近的用户偏好、临时决策               │
└─────────────────────────────────────────────┘
               ↓ (capacity exceeded)
┌─────────────────────────────────────────────┐
│  Session Memory (完整对话历史)               │
│  当前会话的所有消息                           │
│  例如：完整的问答记录                         │
└─────────────────────────────────────────────┘
               ↓ (auto promote + summarize)
┌─────────────────────────────────────────────┐
│  Long-term Memory (跨会话知识库)             │
│  永久存储 + 向量检索                          │
│  例如：用户画像、领域知识、历史决策           │
└─────────────────────────────────────────────┘
```

**v0.1.9 智能晋升**：

```python
# Working Memory → Long-term Memory 时：

# 1. 过滤 trivial 内容
if is_trivial(content):  # "好的"、"谢谢"、"OK" 等
    return  # 不晋升

# 2. 检查最小长度
if len(content) < min_promotion_length:  # 默认 50 字符
    return

# 3. 长文本摘要（可选）
if len(content) > summarization_threshold:  # 默认 100 字符
    # 使用轻量级 LLM（如 gpt-4o-mini）提取关键事实
    content = await summarize_for_longterm(content)
    # 原文: "详细的实现过程..." (500 字符)
    # 摘要: "- 使用 Python 实现\n- 采用递归算法\n- 时间复杂度 O(n)" (80 字符)

# 4. 向量化（异步，不阻塞）
queue_vectorization_task(entry)  # v0.1.9: 后台处理
```

**RAG 检索**：

```python
# 语义检索
results = await memory.retrieve(
    query="用户喜欢什么编程语言",
    top_k=5,
    tier="longterm"
)

# 返回 XML 格式（直接用于 Context Assembly）
"""
<retrieved_memory>
  <memory tier="longterm" relevance="0.92">
    用户偏好：Python（数据分析）、Rust（系统编程）
  </memory>
  <memory tier="longterm" relevance="0.87">
    曾表示喜欢静态类型语言
  </memory>
  ...
</retrieved_memory>
"""
```

### 4. Skills 系统：渐进式披露

**问题**：传统方式将所有能力文档塞入系统提示

```python
# ❌ 传统方式
system_prompt = """
你是助手。

# PDF 分析能力
使用 PyPDF2 库...（1000+ tokens）

# Web 研究能力
使用 requests 库...（1000+ tokens）

# 数据处理能力
使用 pandas 库...（1000+ tokens）

总计：3000+ tokens，每次调用都消耗
"""
```

**Loom Skills 方案**：

```
┌──────────────────────────────────────┐
│  Layer 1: Index (系统提示)            │
│  - pdf_analyzer: PDF 分析工具         │
│  - web_research: Web 研究工具         │
│  - data_processor: 数据处理工具       │
│  ~50 tokens/skill × 3 = 150 tokens   │
└──────────────────────────────────────┘
              ↓ (按需加载)
┌──────────────────────────────────────┐
│  Layer 2: Detailed Docs (SKILL.md)   │
│  完整的使用文档                        │
│  ~500-2000 tokens/skill              │
│  只在需要时加载                        │
└──────────────────────────────────────┘
              ↓ (按需访问)
┌──────────────────────────────────────┐
│  Layer 3: Resources (文件/数据)       │
│  配置文件、模板、数据集                │
│  任意大小                              │
└──────────────────────────────────────┘
```

**效果对比**：
- 传统方式：3 个能力 = 3000+ tokens 每次调用
- Skills 方式：3 个能力 = 150 tokens 索引 + 按需加载详细文档
- **节省 95% 上下文开销**

### 5. 工具并行执行

```python
# Agent 需要调用 3 个工具

# ❌ 其他框架：串行执行
result1 = await tool1()  # 1秒
result2 = await tool2()  # 1秒
result3 = await tool3()  # 1秒
# 总耗时：3秒

# ✅ Loom：自动并行
results = await asyncio.gather(
    tool1(),
    tool2(),
    tool3()
)
# 总耗时：1秒（3x 性能提升）
```

### 6. 完整事件系统

```python
from loom.core.events import AgentEventType

def event_handler(event):
    """实时监控 Agent 执行"""
    if event.type == AgentEventType.LLM_START:
        print("🤖 LLM 调用开始")

    elif event.type == AgentEventType.LLM_END:
        print(f"✅ LLM 完成")
        print(f"   Input tokens: {event.data['tokens_input']}")
        print(f"   Output tokens: {event.data['tokens_output']}")
        print(f"   Cost: ${event.data['cost']:.4f}")

    elif event.type == AgentEventType.TOOL_START:
        print(f"🔧 工具调用: {event.data['tool_name']}")

    elif event.type == AgentEventType.TOOL_END:
        success = event.data['success']
        print(f"   {'✅' if success else '❌'} 工具完成")

agent = loom.agent(
    name="monitored",
    llm=llm,
    tools=[...],
    event_handler=event_handler
)

response = await agent.run(message)

# 查看统计
stats = agent.get_stats()
print(f"LLM 调用次数: {stats['executor_stats']['total_llm_calls']}")
print(f"工具调用次数: {stats['executor_stats']['total_tool_calls']}")
print(f"总 tokens: {stats['executor_stats']['total_tokens_input'] + stats['executor_stats']['total_tokens_output']}")
print(f"总成本: ${stats['executor_stats']['total_cost']:.2f}")
```

---

## 🤝 多 Agent 协作 - Crew

**Crew** 是 Loom 的多智能体协作模式，支持：
- 角色分工（角色定义 + 专属工具）
- 任务委派（Agent 间通信）
- 智能协调（并行执行 + 依赖管理）

```python
from loom.patterns import Crew, CrewRole

# 定义角色
researcher = CrewRole(
    name="researcher",
    description="负责信息收集和研究",
    llm=llm,
    tools=[search, fetch_url]
)

analyst = CrewRole(
    name="analyst",
    description="负责数据分析",
    llm=llm,
    tools=[analyze_data, create_chart]
)

writer = CrewRole(
    name="writer",
    description="负责撰写报告",
    llm=llm,
    tools=[format_markdown]
)

# 创建 Crew
crew = Crew(
    roles=[researcher, analyst, writer],
    orchestration="auto"  # 自动协调
)

# 执行任务
result = await crew.run(
    Message(role="user", content="分析 2024 年 AI Agent 市场趋势并撰写报告")
)

# Crew 自动：
# 1. researcher 搜索信息
# 2. analyst 分析数据（可能并行）
# 3. writer 撰写报告
# 4. 合成最终结果
```

---

## 📚 文档

- [快速开始](docs/getting-started/quickstart.md)
- [核心概念](docs/architecture/overview.md)
- [API 参考](docs/api/README.md)
- [示例](examples/README.md)
- [迁移指南](docs/migration/v0.1.5.md)

---

## 🧪 测试覆盖

v0.1.9 包含 **65 个全面的单元测试**：

```bash
pytest tests/unit/test_message.py                      # 18 个 Message 测试
pytest tests/unit/test_executor_serialization.py       # 18 个序列化测试
pytest tests/unit/test_hierarchical_memory_v0_1_9.py   # 29 个 Memory 测试

# 运行所有测试
pytest tests/unit/ -v

# ============================== 65 passed in 0.47s ==============================
```

---

## 📈 版本历史

### v0.1.9 - 2024-12-15 - 架构清理 & 记忆优化

**重点改进**：类型安全、数据完整性、性能优化

- ✅ Message 架构修复（P0 - 关键）
  - history 声明为正式 dataclass 字段
  - get_message_history() 安全提取函数
  - 修复所有冻结数据类突变
  - 工具结果结构化序列化
  - 消除所有 hasattr() 模式

- ✅ Memory 系统优化（P1 - 用户体验）
  - 智能记忆晋升（LLM 摘要）
  - 异步向量化（后台任务队列）
  - Ephemeral Memory 调试模式

- ✅ 完整测试覆盖（65 个测试全部通过）

详见 [CHANGELOG.md](CHANGELOG.md)

---

## 🤝 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

Loom Agent 受到以下项目的启发：
- LangGraph（图执行模型）
- AutoGen（多智能体协作）
- CrewAI（角色定义）

但采用了完全不同的架构设计，专注于**类型安全**、**数据完整性**和**生产就绪**。

---

<div align="center">

**⭐️ 如果这个项目对你有帮助，请给个 Star！**

[GitHub](https://github.com/kongusen/loom-agent) | [文档](docs/README.md) | [示例](examples/README.md) | [问题反馈](https://github.com/kongusen/loom-agent/issues)

</div>
