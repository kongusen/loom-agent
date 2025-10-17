# Loom Agent v4.0.0 用户使用指南

**版本**: v4.0.0
**最后更新**: 2025-10-16

---

## 📖 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [创建Agent](#创建agent)
4. [工具系统](#工具系统)
5. [RAG模式](#rag模式)
6. [内存管理](#内存管理)
7. [生产环境配置](#生产环境配置)
8. [高级特性](#高级特性)
9. [常见问题](#常见问题)

---

## 快速开始

### 安装

```bash
# 从PyPI安装
pip install loom-agent

# 或从源码安装
git clone https://github.com/your-org/loom-agent.git
cd loom-agent
pip install -e .

# 安装特定provider
pip install "loom-agent[openai]"      # OpenAI
pip install "loom-agent[anthropic]"   # Anthropic Claude
pip install "loom-agent[all]"         # 所有功能
```

### 第一个Agent

```python
import asyncio
from loom import agent

async def main():
    # 最简单的方式：使用环境变量
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        api_key="your-api-key-here"
    )

    result = await my_agent.ainvoke("介绍一下Loom Agent框架")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### 使用环境变量

```bash
# 设置环境变量
export LOOM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export LOOM_MODEL=gpt-4

# Python代码
from loom import agent_from_env

async def main():
    my_agent = agent_from_env()  # 自动从环境变量读取
    result = await my_agent.ainvoke("Hello!")
    print(result)
```

---

## 核心概念

### 1. Agent (智能体)

Agent是Loom框架的核心组件，负责：
- 接收用户输入
- 调用LLM生成响应
- 执行工具调用
- 管理对话历史
- 处理错误和重试

### 2. LLM (大语言模型)

LLM是Agent的"大脑"，支持多种提供商：
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Azure OpenAI
- Google (Gemini)
- Cohere
- Ollama (本地模型)

### 3. Tools (工具)

工具是Agent可以调用的函数，用于：
- 读取/写入文件
- 搜索网络
- 执行代码
- 访问数据库
- 调用API

### 4. Memory (内存)

内存系统管理对话历史：
- InMemoryMemory: 临时内存（进程内）
- PersistentMemory: 持久化内存（跨会话）

### 5. RAG (检索增强生成)

RAG模式通过检索相关文档来增强Agent的回答能力。

---

## 创建Agent

### 方法1: 使用 `loom.agent()` 函数

最简单和推荐的方式：

```python
from loom import agent

# 方式A: 直接指定provider和model
my_agent = agent(
    provider="openai",
    model="gpt-4",
    api_key="sk-...",
    temperature=0.7,
    max_tokens=2000
)

# 方式B: 使用LLM实例
from loom.builtin.llms import OpenAILLM

llm = OpenAILLM(api_key="sk-...", model="gpt-4")
my_agent = agent(llm=llm)

# 方式C: 使用LLMConfig
from loom import LLMConfig, agent

config = LLMConfig.openai(
    api_key="sk-...",
    model="gpt-4",
    temperature=0.7
)
my_agent = agent(config=config)
```

### 方法2: 使用 `loom.agent_from_env()`

从环境变量自动配置：

```python
from loom import agent_from_env

# 需要设置环境变量：
# LOOM_PROVIDER=openai
# LOOM_MODEL=gpt-4
# OPENAI_API_KEY=sk-...

my_agent = agent_from_env()
```

### 方法3: 使用 `Agent` 类

完全控制所有参数：

```python
from loom import Agent
from loom.builtin.llms import OpenAILLM
from loom.builtin.memory import PersistentMemory

llm = OpenAILLM(api_key="sk-...", model="gpt-4")
memory = PersistentMemory()

my_agent = Agent(
    llm=llm,
    memory=memory,
    max_iterations=50,
    max_context_tokens=16000,
    system_instructions="You are a helpful assistant."
)
```

### Agent参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `llm` | BaseLLM | 必需 | 语言模型实例 |
| `tools` | List[BaseTool] | None | 工具列表 |
| `memory` | BaseMemory | InMemoryMemory | 内存系统 |
| `compressor` | BaseCompressor | 自动 | 上下文压缩器 |
| `max_iterations` | int | 50 | 最大迭代次数 |
| `max_context_tokens` | int | 16000 | 最大上下文token数 |
| `system_instructions` | str | None | 系统提示词 |
| `callbacks` | List[BaseCallback] | None | 回调函数列表 |
| `safe_mode` | bool | False | 安全模式（需要确认工具调用） |

### 运行Agent

```python
# 方式1: 使用 run() 或 ainvoke()
result = await my_agent.run("你好，介绍一下你自己")
result = await my_agent.ainvoke("同上")  # LangChain风格别名

# 方式2: 流式输出
async for event in my_agent.stream("讲个故事"):
    if event.type == "text":
        print(event.content, end="", flush=True)

# 方式3: 带取消令牌（v4.0.0新特性）
import asyncio

cancel_token = asyncio.Event()

# 在另一个任务中可以取消
# cancel_token.set()

result = await my_agent.run(
    "执行长时间任务",
    cancel_token=cancel_token,
    correlation_id="req-123"  # 用于追踪
)
```

---

## 工具系统

### 创建自定义工具

#### 方式1: 使用 `@tool` 装饰器（推荐）

```python
from loom import tool, agent

@tool()
def add(a: int, b: int) -> int:
    """将两个整数相加"""
    return a + b

@tool()
def search_web(query: str, max_results: int = 5) -> str:
    """搜索网络并返回结果"""
    # 实现搜索逻辑
    return f"搜索结果: {query}"

# 创建带工具的Agent
my_agent = agent(
    provider="openai",
    model="gpt-4",
    api_key="sk-...",
    tools=[add(), search_web()]
)

# Agent会自动调用工具
result = await my_agent.run("3加5等于多少？")
```

#### 方式2: 继承 `BaseTool` 类

```python
from loom.interfaces.tool import BaseTool
from pydantic import BaseModel, Field

class CalculatorArgs(BaseModel):
    expression: str = Field(description="要计算的数学表达式")

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "计算数学表达式"
    args_schema = CalculatorArgs

    async def run(self, expression: str) -> str:
        try:
            result = eval(expression)  # 生产环境请使用安全的方式
            return f"结果: {result}"
        except Exception as e:
            return f"错误: {str(e)}"

# 使用
my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[CalculatorTool()]
)
```

### 异步工具

```python
import aiohttp
from loom import tool

@tool()
async def fetch_url(url: str) -> str:
    """异步获取URL内容"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[fetch_url()]
)
```

### 工具并发执行

v4.0.0支持自动并发执行工具（10x性能提升）：

```python
@tool(concurrency_safe=True)  # 默认为True
def read_file(path: str) -> str:
    """读取文件内容（并发安全）"""
    with open(path) as f:
        return f.read()

@tool(concurrency_safe=False)  # 写操作不并发
def write_file(path: str, content: str) -> str:
    """写入文件内容"""
    with open(path, 'w') as f:
        f.write(content)
    return "写入成功"

# Agent会自动处理：
# - read操作并发执行
# - write操作串行执行（相同文件）
```

---

## RAG模式

### 什么是RAG？

RAG（Retrieval-Augmented Generation，检索增强生成）通过从知识库检索相关文档来增强LLM的回答能力。

### 基础RAG示例

```python
from loom import agent
from loom.patterns.rag import RAGPattern
from loom.builtin.retrievers import ChromaRetriever

# 1. 创建Agent
my_agent = agent(provider="openai", model="gpt-4")

# 2. 创建检索器（需要先构建向量数据库）
retriever = ChromaRetriever(
    collection_name="my_docs",
    persist_directory="./chroma_db"
)

# 3. 创建RAG Pattern
rag = RAGPattern(
    agent=my_agent,
    retriever=retriever,
    top_k=5  # 检索前5个文档
)

# 4. 使用RAG回答问题
result = await rag.run("Loom框架的主要特性是什么？")
print(result)
```

### 高级RAG: 多查询RAG

生成多个查询变体以提高召回率：

```python
from loom.patterns.rag import MultiQueryRAG

rag = MultiQueryRAG(
    agent=my_agent,
    retriever=retriever,
    query_count=3,  # 生成3个查询变体
    top_k=10,
    rerank_top_k=3
)

result = await rag.run("如何优化Agent性能？")
```

### 层次化RAG

先检索文档，再检索段落：

```python
from loom.patterns.rag import HierarchicalRAG

rag = HierarchicalRAG(
    agent=my_agent,
    document_retriever=doc_retriever,
    paragraph_retriever=para_retriever,
    doc_top_k=5,
    para_top_k=3
)

result = await rag.run("详细解释错误处理机制")
```

### 使用RAG工具

将RAG作为工具集成到Agent：

```python
from loom import tool

@tool()
async def search_docs(query: str) -> str:
    """搜索文档知识库"""
    docs = await retriever.retrieve(query, top_k=3)
    return "\n\n".join([doc.content for doc in docs])

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[search_docs()],
    system_instructions="当需要查找文档时，使用search_docs工具。"
)

result = await my_agent.run("查找关于压缩管理器的文档")
```

---

## 内存管理

### 内存类型

#### 1. InMemoryMemory（默认）

进程内临时内存，进程结束后丢失：

```python
from loom import Agent
from loom.builtin.memory import InMemoryMemory

memory = InMemoryMemory()

my_agent = Agent(llm=llm, memory=memory)
```

#### 2. PersistentMemory（推荐）

跨会话持久化内存，自动保存到磁盘：

```python
from loom import Agent
from loom.builtin.memory import PersistentMemory

memory = PersistentMemory(
    persist_dir=".loom",          # 保存目录
    session_id="user_123",        # 会话ID（可选）
    enable_persistence=True,      # 启用持久化
    auto_backup=True,             # 自动备份
    max_backup_files=5            # 最多保留5个备份
)

my_agent = Agent(llm=llm, memory=memory)

# 对话会自动保存
await my_agent.run("你好")
await my_agent.run("我刚才说了什么？")  # 记得上一句

# 重启程序后，使用相同session_id可以恢复对话
```

### 内存操作

```python
# 获取所有消息
messages = memory.get_messages()

# 添加消息
from loom.core.types import Message, MessageRole

memory.add_message(Message(
    role=MessageRole.USER,
    content="Hello"
))

# 清空内存
memory.clear()

# 获取持久化信息
info = memory.get_persistence_info()
print(f"会话文件: {info['session_file']}")
print(f"备份数量: {info['backup_count']}")
```

### 上下文压缩

v4.0.0自动压缩功能（92%阈值触发）：

```python
from loom import Agent

# 默认已启用压缩，无需额外配置
my_agent = Agent(
    llm=llm,
    max_context_tokens=16000  # 达到92%时自动压缩
)

# 压缩后可以进行5倍更长的对话
for i in range(100):
    await my_agent.run(f"这是第{i}轮对话")
    # Agent会自动压缩历史，保持上下文在限制内
```

---

## 生产环境配置

### 基础生产配置

```python
from loom import Agent
from loom.builtin.memory import PersistentMemory
from loom.callbacks.observability import ObservabilityCallback, MetricsAggregator

# 1. 持久化内存
memory = PersistentMemory()

# 2. 可观测性回调
obs_callback = ObservabilityCallback()
metrics = MetricsAggregator()

# 3. 创建生产级Agent
my_agent = Agent(
    llm=llm,
    memory=memory,
    callbacks=[obs_callback, metrics],
    max_iterations=50,
    max_context_tokens=16000
)

# 4. 运行
result = await my_agent.run("处理用户请求")

# 5. 查看指标
summary = metrics.get_summary()
print(f"LLM调用次数: {summary['llm_calls']}")
print(f"平均延迟: {summary.get('avg_llm_latency_ms', 0):.2f}ms")
print(f"错误率: {summary.get('errors_per_minute', 0):.2f}/min")
```

### 企业级配置（完整功能栈）

```python
from loom import (
    Agent,
    PersistentMemory,
    ModelPoolLLM,
    ModelConfig,
    ObservabilityCallback,
    MetricsAggregator,
    RetryPolicy,
    CircuitBreaker,
)
from loom.builtin.llms import OpenAILLM

# 1. 创建主LLM和备用LLM
gpt4 = OpenAILLM(api_key="sk-...", model="gpt-4")
gpt35 = OpenAILLM(api_key="sk-...", model="gpt-3.5-turbo")

# 2. 配置模型池（自动故障转移）
pool_llm = ModelPoolLLM([
    ModelConfig("gpt-4", gpt4, priority=100),      # 主模型
    ModelConfig("gpt-3.5", gpt35, priority=50),    # 备用模型
])

# 3. 持久化内存
memory = PersistentMemory(
    session_id="production_session",
    max_backup_files=10
)

# 4. 可观测性
obs = ObservabilityCallback()
metrics = MetricsAggregator()

# 5. 弹性组件
retry_policy = RetryPolicy(
    max_retries=3,
    base_delay=1.0,
    exponential_base=2.0
)
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout_seconds=60
)

# 6. 创建企业级Agent
my_agent = Agent(
    llm=pool_llm,
    memory=memory,
    callbacks=[obs, metrics],
    tools=your_tools,
    system_instructions="你是一个专业的AI助手。"
)

# 7. 使用弹性包装执行
async def robust_run(prompt: str) -> str:
    """带重试和熔断器的执行"""
    return await retry_policy.execute_with_retry(
        circuit_breaker.call,
        my_agent.run,
        prompt
    )

# 8. 执行
try:
    result = await robust_run("用户请求")
    print(result)
except Exception as e:
    print(f"请求失败: {e}")

# 9. 监控健康状况
health = pool_llm.get_health_summary()
for model_id, status in health.items():
    print(f"{model_id}: {status['status']} (成功率: {status['success_rate']*100:.1f}%)")
```

### 结构化日志

```python
from loom.core.structured_logger import get_logger, set_correlation_id

# 创建logger
logger = get_logger("my_app")

# 设置关联ID（跨请求追踪）
set_correlation_id("req-12345")

# 所有日志自动包含关联ID和JSON格式
logger.info("处理请求", user_id="user_456", action="query")
# 输出: {"timestamp": "...", "level": "INFO", "correlation_id": "req-12345", ...}

# 性能日志
logger.log_performance("llm_call", duration_ms=234.5, tokens=150)
```

---

## 高级特性

### 1. 实时取消（v4.0.0）

```python
import asyncio

cancel_token = asyncio.Event()

# 启动长时间任务
task = asyncio.create_task(
    my_agent.run("执行长时间分析", cancel_token=cancel_token)
)

# 5秒后取消
await asyncio.sleep(5)
cancel_token.set()  # 触发取消

try:
    result = await task
except asyncio.CancelledError:
    print("任务已取消")
```

### 2. 子Agent隔离

```python
from loom.core.subagent_pool import SubAgentPool

pool = SubAgentPool(max_depth=3)

# 创建隔离的子Agent
result = await pool.spawn(
    llm=llm,
    prompt="分析这段代码",
    tool_whitelist=["read_file", "analyze_code"],  # 只允许这些工具
    timeout_seconds=60,
    max_iterations=20
)

# 子Agent失败不会影响主Agent
```

### 3. 并发子Agent

```python
# 并发执行多个子Agent
results = await pool.spawn_many([
    {"llm": llm, "prompt": "任务1", "tool_whitelist": ["tool1"]},
    {"llm": llm, "prompt": "任务2", "tool_whitelist": ["tool2"]},
    {"llm": llm, "prompt": "任务3", "tool_whitelist": ["tool3"]},
])

for i, result in enumerate(results):
    print(f"任务{i+1}结果: {result}")
```

### 4. 系统提醒

自动生成运行时提示：

```python
from loom.core.system_reminders import SystemReminderManager

manager = SystemReminderManager()

# 检查当前状态
context = {
    "current_tokens": 15000,
    "max_tokens": 16000,
    "metrics": {"total_errors": 3, "total_operations": 10}
}

reminders = manager.check_all(context)
# 输出: ["⚠️ WARNING: Memory usage is high (93.8%)", ...]

# 自动注入到系统提示
enhanced_prompt = manager.inject_into_context(context, system_prompt)
```

### 5. 权限控制

```python
my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[read_file(), write_file(), delete_file()],
    permission_policy={
        "read_file": "allow",
        "write_file": "ask",     # 需要用户确认
        "delete_file": "deny"    # 禁止
    },
    safe_mode=True  # 启用安全模式
)
```

### 6. 流式输出

```python
async for event in my_agent.stream("讲个长故事"):
    if event.type == "text":
        print(event.content, end="", flush=True)
    elif event.type == "tool_call":
        print(f"\n[调用工具: {event.tool_name}]")
    elif event.type == "tool_result":
        print(f"[工具返回: {event.result}]")
```

---

## 常见问题

### Q1: 如何选择合适的LLM？

**答**: 根据任务选择：
- **GPT-4**: 复杂推理、代码生成、高质量输出
- **GPT-3.5-turbo**: 快速响应、成本优化
- **Claude**: 长文本处理、安全对话
- **Ollama**: 本地部署、隐私保护

### Q2: 如何优化成本？

**答**:
1. 使用较小的模型（如gpt-3.5-turbo）
2. 启用上下文压缩（默认启用）
3. 设置合理的`max_tokens`
4. 使用模型池在主/备用模型间切换

```python
pool_llm = ModelPoolLLM([
    ModelConfig("gpt-4", gpt4, priority=100),      # 复杂任务
    ModelConfig("gpt-3.5", gpt35, priority=50),    # 简单任务
])
```

### Q3: Agent无响应怎么办？

**答**:
1. 检查API密钥是否正确
2. 检查网络连接
3. 使用取消令牌设置超时
4. 查看日志排查问题

```python
import asyncio

cancel_token = asyncio.Event()

async def timeout_wrapper():
    task = asyncio.create_task(
        my_agent.run("query", cancel_token=cancel_token)
    )
    try:
        return await asyncio.wait_for(task, timeout=30.0)
    except asyncio.TimeoutError:
        cancel_token.set()
        raise
```

### Q4: 如何处理大文件？

**答**: 使用RAG模式将文件切块存入向量数据库：

```python
from loom.builtin.retrievers import ChromaRetriever

# 1. 构建索引
retriever = ChromaRetriever(collection_name="docs")
await retriever.add_documents([
    Document(content=chunk1, metadata={"source": "file1.txt"}),
    Document(content=chunk2, metadata={"source": "file1.txt"}),
])

# 2. 使用RAG查询
rag = RAGPattern(agent=my_agent, retriever=retriever)
result = await rag.run("文件中的关键信息是什么？")
```

### Q5: 如何调试Agent？

**答**:
1. 启用详细日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. 使用回调查看事件：
```python
from loom.callbacks.base import BaseCallback

class DebugCallback(BaseCallback):
    async def on_llm_start(self, messages, **kwargs):
        print(f"LLM输入: {messages}")

    async def on_llm_end(self, response, **kwargs):
        print(f"LLM输出: {response}")

my_agent = Agent(llm=llm, callbacks=[DebugCallback()])
```

3. 查看指标：
```python
summary = metrics.get_summary()
print(summary)
```

### Q6: 如何实现多轮对话？

**答**: 使用持久化内存自动管理：

```python
from loom.builtin.memory import PersistentMemory

memory = PersistentMemory(session_id="user_123")
my_agent = Agent(llm=llm, memory=memory)

# 第1轮
await my_agent.run("我叫张三")

# 第2轮
result = await my_agent.run("我叫什么名字？")
# 输出: "你叫张三"
```

### Q7: 如何集成到Web应用？

**答**: 使用FastAPI示例：

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    session_id: str

@app.post("/chat")
async def chat(request: QueryRequest):
    try:
        memory = PersistentMemory(session_id=request.session_id)
        agent = Agent(llm=llm, memory=memory)
        result = await agent.run(request.query)
        return {"response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Q8: 如何实现流式响应到前端？

**答**: 使用SSE（Server-Sent Events）：

```python
from fastapi.responses import StreamingResponse

@app.get("/chat/stream")
async def chat_stream(query: str):
    async def event_generator():
        async for event in my_agent.stream(query):
            if event.type == "text":
                yield f"data: {event.content}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

---

## 下一步

- 查看 [V4_FINAL_SUMMARY.md](V4_FINAL_SUMMARY.md) 了解v4.0.0所有特性
- 查看 [examples/](examples/) 目录获取更多示例
- 查看 [CHANGELOG.md](CHANGELOG.md) 了解版本变化
- 查看 [P2_FEATURES.md](P2_FEATURES.md) 了解生产级特性

---

## 获取帮助

- GitHub Issues: [https://github.com/your-org/loom-agent/issues](https://github.com/your-org/loom-agent/issues)
- 文档: [https://docs.loom-agent.dev](https://docs.loom-agent.dev)

---

**Happy Coding with Loom Agent v4.0.0!** 🎉
