# Loom Agent v0.1.1 API 参考文档

**版本**: v0.1.1
**最后更新**: 2025-12-12

---

## 目录

1. [Agent API](#agent-api)
2. [Builder Functions](#builder-functions)
3. [Tools API](#tools-api)
4. [Memory API](#memory-api)
5. [RAG API](#rag-api)
6. [LLM API](#llm-api)
7. [Callbacks API](#callbacks-api)
8. [Resilience API](#resilience-api)
9. [Observability API](#observability-api)

---

## Agent API

### Agent 类

```python
from loom import Agent

agent = Agent(
    llm: BaseLLM,
    tools: List[BaseTool] | None = None,
    memory: Optional[BaseMemory] = None,
    compressor: Optional[BaseCompressor] = None,
    max_iterations: int = 50,
    max_context_tokens: int = 16000,
    permission_policy: Optional[Dict[str, str]] = None,
    ask_handler = None,
    safe_mode: bool = False,
    permission_store = None,
    context_retriever = None,
    system_instructions: Optional[str] = None,
    callbacks: Optional[List[BaseCallback]] = None,
    steering_control: Optional[SteeringControl] = None,
    metrics: Optional[MetricsCollector] = None,
)
```

#### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `llm` | `BaseLLM` | 必需 | 语言模型实例 |
| `tools` | `List[BaseTool]` | `None` | Agent可用的工具列表 |
| `memory` | `BaseMemory` | `InMemoryMemory()` | 内存管理系统 |
| `compressor` | `BaseCompressor` | 自动创建 | 上下文压缩器（v0.1.1自动启用） |
| `max_iterations` | `int` | `50` | 最大执行迭代次数 |
| `max_context_tokens` | `int` | `16000` | 最大上下文token限制 |
| `permission_policy` | `Dict[str, str]` | `None` | 工具权限策略 |
| `ask_handler` | `Callable` | `None` | 用户确认处理器 |
| `safe_mode` | `bool` | `False` | 安全模式（所有工具需确认） |
| `permission_store` | `PermissionStore` | `None` | 权限持久化存储 |
| `context_retriever` | `BaseRetriever` | `None` | 上下文检索器 |
| `system_instructions` | `str` | `None` | 系统提示词 |
| `callbacks` | `List[BaseCallback]` | `None` | 事件回调列表 |
| `steering_control` | `SteeringControl` | 自动创建 | 实时控制器 |
| `metrics` | `MetricsCollector` | `None` | 指标收集器 |

#### 方法

##### `async run(input: str, cancel_token: Optional[asyncio.Event] = None, correlation_id: Optional[str] = None) -> str`

执行Agent任务并返回结果。

**参数**:
- `input` (str): 用户输入
- `cancel_token` (asyncio.Event): 取消令牌（v0.1.1新增）
- `correlation_id` (str): 请求追踪ID（v0.1.1新增）

**返回**:
- `str`: Agent的响应

**示例**:
```python
result = await agent.run("你好，介绍一下你自己")

# 带取消令牌
cancel_token = asyncio.Event()
result = await agent.run(
    "执行长任务",
    cancel_token=cancel_token,
    correlation_id="req-123"
)
```

##### `async ainvoke(input: str, cancel_token: Optional[asyncio.Event] = None, correlation_id: Optional[str] = None) -> str`

`run()` 的别名，兼容LangChain风格API。

##### `get_metrics() -> Dict`

获取当前Agent的运行指标。

**返回**:
- `Dict`: 指标摘要

**示例**:
```python
metrics = agent.get_metrics()
print(f"总迭代次数: {metrics['iterations']}")
```

---

## Builder Functions

### `loom.agent()`

便捷函数，快速创建Agent实例。

```python
from loom import agent

my_agent = agent(
    # LLM配置（三选一）
    llm: Optional[BaseLLM] = None,
    config: Optional[LLMConfig] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,

    # Agent选项
    tools: Optional[List[BaseTool]] = None,
    memory: Optional[BaseMemory] = None,
    compressor: Optional[BaseCompressor] = None,
    max_iterations: int = 50,
    max_context_tokens: int = 16000,
    permission_policy: Optional[Dict[str, str]] = None,
    ask_handler = None,
    safe_mode: bool = False,
    permission_store = None,

    # LLM额外配置
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,

    # 高级选项
    context_retriever = None,
    system_instructions: Optional[str] = None,
    callbacks: Optional[list[BaseCallback]] = None,
    steering_control: Optional[SteeringControl] = None,
    metrics: Optional[MetricsCollector] = None,
)
```

#### 使用方式

**方式1: 直接指定provider和model**
```python
agent = loom.agent(
    provider="openai",
    model="gpt-4",
    api_key="sk-...",
    temperature=0.7
)
```

**方式2: 传入LLM实例**
```python
from loom.builtin.llms import OpenAILLM

llm = OpenAILLM(api_key="sk-...", model="gpt-4")
agent = loom.agent(llm=llm)
```

**方式3: 使用LLMConfig**
```python
from loom import LLMConfig

config = LLMConfig.openai(api_key="sk-...", model="gpt-4")
agent = loom.agent(config=config)
```

### `loom.agent_from_env()`

从环境变量创建Agent。

```python
from loom import agent_from_env

my_agent = agent_from_env(
    provider: Optional[str] = None,  # 覆盖LOOM_PROVIDER
    model: Optional[str] = None,     # 覆盖LOOM_MODEL
    # ... 其他参数同agent()
)
```

**环境变量**:
- `LOOM_PROVIDER`: 提供商（openai, anthropic等）
- `LOOM_MODEL`: 模型名称
- `OPENAI_API_KEY`: OpenAI API密钥
- `ANTHROPIC_API_KEY`: Anthropic API密钥
- `OPENAI_BASE_URL`: 自定义API端点

**示例**:
```bash
export LOOM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export LOOM_MODEL=gpt-4
```

```python
agent = loom.agent_from_env()
```

---

## Tools API

### `@tool` 装饰器

将Python函数转换为Tool。

```python
from loom import tool

@tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    args_schema: Optional[Type[BaseModel]] = None,
    concurrency_safe: bool = True
)
def your_function(...) -> ...:
    ...
```

#### 参数

- `name` (str): 工具名称（默认使用函数名）
- `description` (str): 工具描述（默认使用docstring）
- `args_schema` (Type[BaseModel]): 参数schema（默认自动推断）
- `concurrency_safe` (bool): 是否并发安全（默认True）

#### 示例

```python
@tool()
def add(a: int, b: int) -> int:
    """将两个数相加"""
    return a + b

@tool(name="multiply", description="乘法运算")
def mul(x: float, y: float) -> float:
    return x * y

@tool(concurrency_safe=False)
def write_file(path: str, content: str) -> str:
    """写入文件（不并发安全）"""
    with open(path, 'w') as f:
        f.write(content)
    return "成功"

# 异步工具
@tool()
async def fetch_url(url: str) -> str:
    """异步获取URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()
```

### `BaseTool` 基类

自定义工具的基类。

```python
from loom.interfaces.tool import BaseTool
from pydantic import BaseModel

class YourTool(BaseTool):
    name: str = "tool_name"
    description: str = "工具描述"
    args_schema: Type[BaseModel] = YourArgsModel

    async def run(self, **kwargs) -> Any:
        # 实现工具逻辑
        return result

    @property
    def is_concurrency_safe(self) -> bool:
        return True
```

---

## Memory API

### `InMemoryMemory` 类

进程内临时内存。

```python
from loom.builtin.memory import InMemoryMemory

memory = InMemoryMemory()
```

#### 方法

##### `add_message(message: Message) -> None`

添加消息到内存。

```python
from loom.core.types import Message, MessageRole

memory.add_message(Message(
    role=MessageRole.USER,
    content="Hello"
))
```

##### `get_messages() -> List[Message]`

获取所有消息。

```python
messages = memory.get_messages()
```

##### `clear() -> None`

清空内存。

```python
memory.clear()
```

### `PersistentMemory` 类

跨会话持久化内存。

```python
from loom.builtin.memory import PersistentMemory

memory = PersistentMemory(
    persist_dir: str = ".loom",
    session_id: Optional[str] = None,
    enable_persistence: bool = True,
    auto_backup: bool = True,
    max_backup_files: int = 5
)
```

#### 参数

- `persist_dir` (str): 持久化目录
- `session_id` (str): 会话ID（默认自动生成）
- `enable_persistence` (bool): 启用持久化
- `auto_backup` (bool): 自动备份
- `max_backup_files` (int): 最大备份文件数

#### 方法

继承自`InMemoryMemory`的所有方法，额外增加：

##### `get_persistence_info() -> Dict`

获取持久化信息。

```python
info = memory.get_persistence_info()
print(f"会话文件: {info['session_file']}")
print(f"备份数量: {info['backup_count']}")
```

##### `add_compression_metadata(metadata: dict) -> None`

添加压缩元数据。

```python
memory.add_compression_metadata({
    "original_tokens": 10000,
    "compressed_tokens": 2500,
    "compression_ratio": 0.75
})
```

---

## RAG API

### `RAGPattern` 类

基础RAG模式。

```python
from loom.patterns.rag import RAGPattern

rag = RAGPattern(
    agent: Agent,
    retriever: BaseRetriever,
    reranker: Optional[callable] = None,
    top_k: int = 5,
    rerank_top_k: int = 3
)
```

#### 参数

- `agent` (Agent): Agent实例
- `retriever` (BaseRetriever): 检索器
- `reranker` (callable): 重排序函数
- `top_k` (int): 初始检索文档数
- `rerank_top_k` (int): 重排序后保留数

#### 方法

##### `async run(query: str) -> str`

执行RAG流程。

```python
result = await rag.run("查询问题")
```

### `MultiQueryRAG` 类

多查询RAG模式。

```python
from loom.patterns.rag import MultiQueryRAG

rag = MultiQueryRAG(
    agent: Agent,
    retriever: BaseRetriever,
    reranker: Optional[callable] = None,
    top_k: int = 5,
    rerank_top_k: int = 3,
    query_count: int = 3  # 额外参数
)
```

### `HierarchicalRAG` 类

层次化RAG模式。

```python
from loom.patterns.rag import HierarchicalRAG

rag = HierarchicalRAG(
    agent: Agent,
    document_retriever: BaseRetriever,
    paragraph_retriever: Optional[BaseRetriever] = None,
    doc_top_k: int = 5,
    para_top_k: int = 3
)
```

---

## LLM API

### `LLMConfig` 类

LLM配置类。

```python
from loom import LLMConfig

# OpenAI
config = LLMConfig.openai(
    api_key: str,
    model: str = "gpt-4",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    base_url: Optional[str] = None
)

# Anthropic
config = LLMConfig.anthropic(
    api_key: str,
    model: str = "claude-3-opus-20240229",
    temperature: float = 0.7,
    max_tokens: int = 2000
)

# Azure OpenAI
config = LLMConfig.azure_openai(
    api_key: str,
    deployment_name: str,
    endpoint: str,
    temperature: float = 0.7,
    max_tokens: int = 2000
)

# Ollama
config = LLMConfig.ollama(
    model: str,
    base_url: str = "http://localhost:11434",
    temperature: float = 0.7
)
```

### `ModelPoolLLM` 类

模型池（自动故障转移）。

```python
from loom import ModelPoolLLM, ModelConfig

pool = ModelPoolLLM(
    models: List[ModelConfig],
    max_fallback_attempts: int = 3
)
```

#### ModelConfig

```python
from loom import ModelConfig

config = ModelConfig(
    model_id: str,           # 模型ID
    llm: BaseLLM,            # LLM实例
    priority: int = 0,       # 优先级（越高越优先）
    max_concurrent: int = 10 # 最大并发数
)
```

#### 示例

```python
from loom import ModelPoolLLM, ModelConfig
from loom.builtin.llms import OpenAILLM

gpt4 = OpenAILLM(model="gpt-4")
gpt35 = OpenAILLM(model="gpt-3.5-turbo")

pool = ModelPoolLLM([
    ModelConfig("gpt-4", gpt4, priority=100),
    ModelConfig("gpt-3.5", gpt35, priority=50)
])

# 像普通LLM一样使用
agent = Agent(llm=pool)
```

#### 方法

##### `get_health_summary() -> Dict`

获取所有模型的健康状态。

```python
health = pool.get_health_summary()
# {
#   "gpt-4": {"status": "healthy", "success_rate": 0.98},
#   "gpt-3.5": {"status": "healthy", "success_rate": 0.95}
# }
```

---

## Callbacks API

### `BaseCallback` 基类

自定义回调的基类。

```python
from loom.callbacks.base import BaseCallback

class MyCallback(BaseCallback):
    async def on_llm_start(self, messages, **kwargs):
        print("LLM开始")

    async def on_llm_end(self, response, **kwargs):
        print(f"LLM结束: {response}")

    async def on_tool_start(self, tool_name, tool_input, **kwargs):
        print(f"工具开始: {tool_name}")

    async def on_tool_end(self, tool_name, tool_output, **kwargs):
        print(f"工具结束: {tool_name}")

    async def on_tool_error(self, tool_name, error, **kwargs):
        print(f"工具错误: {tool_name} - {error}")
```

### `ObservabilityCallback` 类

结构化日志回调。

```python
from loom.callbacks.observability import ObservabilityCallback

callback = ObservabilityCallback(logger: Optional[StructuredLogger] = None)
```

自动记录所有Agent事件到JSON日志。

### `MetricsAggregator` 类

指标聚合回调。

```python
from loom.callbacks.observability import MetricsAggregator

metrics = MetricsAggregator()
```

#### 方法

##### `get_summary() -> Dict`

获取指标摘要。

```python
summary = metrics.get_summary()
# {
#   "llm_calls": 10,
#   "tool_calls": 5,
#   "avg_llm_latency_ms": 234.5,
#   "errors": 1,
#   "uptime_seconds": 120.5
# }
```

---

## Resilience API

### `ErrorClassifier` 类

错误分类器。

```python
from loom import ErrorClassifier

category = ErrorClassifier.classify(error)
is_retryable = ErrorClassifier.is_retryable(error)
guidance = ErrorClassifier.get_recovery_guidance(error)
```

#### 错误类别

```python
from loom.core.error_classifier import ErrorCategory

ErrorCategory.NETWORK_ERROR      # 网络错误
ErrorCategory.TIMEOUT_ERROR      # 超时错误
ErrorCategory.RATE_LIMIT_ERROR   # 速率限制
ErrorCategory.SERVICE_ERROR      # 服务错误（5xx）
ErrorCategory.VALIDATION_ERROR   # 验证错误
ErrorCategory.AUTH_ERROR         # 认证错误
ErrorCategory.NOT_FOUND_ERROR    # 未找到
ErrorCategory.UNKNOWN_ERROR      # 未知错误
```

### `RetryPolicy` 类

重试策略（指数退避）。

```python
from loom import RetryPolicy

policy = RetryPolicy(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
)
```

#### 方法

##### `async execute_with_retry(func, *args, **kwargs) -> Any`

带重试执行函数。

```python
result = await policy.execute_with_retry(
    my_function,
    arg1,
    arg2,
    kwarg1=value1
)
```

### `CircuitBreaker` 类

熔断器。

```python
from loom import CircuitBreaker, CircuitBreakerConfig

breaker = CircuitBreaker(
    config: Optional[CircuitBreakerConfig] = None,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout_seconds: float = 60.0
)
```

#### 方法

##### `async call(func, *args, **kwargs) -> Any`

通过熔断器调用函数。

```python
result = await breaker.call(my_function, arg1, arg2)
```

##### `get_state() -> CircuitState`

获取熔断器状态。

```python
from loom import CircuitState

state = breaker.get_state()
# CircuitState.CLOSED   - 正常
# CircuitState.OPEN     - 熔断
# CircuitState.HALF_OPEN - 半开（测试恢复）
```

##### `reset() -> None`

重置熔断器。

```python
breaker.reset()
```

---

## Observability API

### `StructuredLogger` 类

结构化JSON日志。

```python
from loom.core.structured_logger import StructuredLogger, get_logger, set_correlation_id

# 创建logger
logger = get_logger("my_app")

# 设置关联ID
set_correlation_id("req-123")

# 记录日志
logger.info("消息", extra_field="value")
logger.error("错误", error=str(e))
logger.log_performance("operation", duration_ms=100, tokens=50)
```

#### 方法

##### `info(message: str, **extra) -> None`

记录INFO级别日志。

##### `warning(message: str, **extra) -> None`

记录WARNING级别日志。

##### `error(message: str, exc_info: Optional[Exception] = None, **extra) -> None`

记录ERROR级别日志。

##### `log_performance(operation: str, duration_ms: float, **extra) -> None`

记录性能指标。

### `SystemReminderManager` 类

系统提醒管理器。

```python
from loom.core.system_reminders import SystemReminderManager, get_reminder_manager

manager = SystemReminderManager()
```

#### 方法

##### `check_all(context: dict) -> List[str]`

检查所有规则并返回提醒。

```python
context = {
    "current_tokens": 15000,
    "max_tokens": 16000,
    "metrics": {"total_errors": 3}
}

reminders = manager.check_all(context)
# ["⚠️ WARNING: Memory usage is high (93.8%)", ...]
```

##### `inject_into_context(context: dict, system_prompt: str) -> str`

将提醒注入到系统提示。

```python
enhanced_prompt = manager.inject_into_context(context, system_prompt)
```

### `ModelHealthChecker` 类

模型健康监控。

```python
from loom.llm.model_health import ModelHealthChecker, HealthStatus

checker = ModelHealthChecker(
    success_rate_window: int = 100,
    consecutive_failure_threshold: int = 5,
    degraded_threshold: float = 0.8,
    unhealthy_threshold: float = 0.5
)
```

#### 方法

##### `record_success(model_id: str, latency_ms: float) -> None`

记录成功调用。

```python
checker.record_success("gpt-4", latency_ms=234.5)
```

##### `record_failure(model_id: str, error: str) -> None`

记录失败调用。

```python
checker.record_failure("gpt-4", error="timeout")
```

##### `get_status(model_id: str) -> HealthStatus`

获取模型健康状态。

```python
status = checker.get_status("gpt-4")
# HealthStatus.HEALTHY
# HealthStatus.DEGRADED
# HealthStatus.UNHEALTHY
```

##### `get_metrics(model_id: str) -> Optional[HealthMetrics]`

获取详细指标。

```python
metrics = checker.get_metrics("gpt-4")
print(f"成功率: {metrics.success_rate}")
print(f"平均延迟: {metrics.avg_latency_ms}ms")
```

---

## 类型定义

### `Message` 类

消息对象。

```python
from loom.core.types import Message, MessageRole

message = Message(
    role: MessageRole,
    content: str,
    tool_calls: Optional[List[ToolCall]] = None,
    name: Optional[str] = None
)
```

### `MessageRole` 枚举

```python
from loom.core.types import MessageRole

MessageRole.SYSTEM      # 系统消息
MessageRole.USER        # 用户消息
MessageRole.ASSISTANT   # 助手消息
MessageRole.TOOL        # 工具返回消息
```

### `AgentEvent` 类

实时事件流（新架构）。

```python
from loom.core.events import AgentEvent, AgentEventType

# AgentEvent通过execute()方法产生
async for event in agent.execute("任务"):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")
    elif event.type == AgentEventType.TOOL_RESULT:
        print(f"\n工具: {event.tool_result.tool_name}")
```

**事件类型**:
- `LLM_DELTA`: LLM文本增量
- `TOOL_RESULT`: 工具执行结果
- `AGENT_FINISH`: 任务完成
- `ERROR`: 错误事件


---

## 异常

### `LoomException` 基类

所有Loom异常的基类。

```python
from loom.core.errors import LoomException

class LoomException(Exception):
    category: ErrorCategory
```

### 具体异常

```python
from loom.core.errors import (
    LLMException,           # LLM相关错误
    ToolException,          # 工具执行错误
    MemoryException,        # 内存操作错误
    ValidationError,        # 验证错误
    PermissionDeniedError,  # 权限拒绝
    CancellationError,      # 任务取消
    CircuitBreakerOpenError # 熔断器打开
)
```

---

## 示例汇总

### 完整企业级配置

```python
from loom import (
    Agent,
    agent,
    PersistentMemory,
    ModelPoolLLM,
    ModelConfig,
    ObservabilityCallback,
    MetricsAggregator,
    RetryPolicy,
    CircuitBreaker,
    tool,
)
from loom.builtin.llms import OpenAILLM

# 1. 创建工具
@tool()
def search(query: str) -> str:
    """搜索知识库"""
    return f"搜索结果: {query}"

# 2. 配置模型池
gpt4 = OpenAILLM(model="gpt-4")
gpt35 = OpenAILLM(model="gpt-3.5-turbo")

pool_llm = ModelPoolLLM([
    ModelConfig("gpt-4", gpt4, priority=100),
    ModelConfig("gpt-3.5", gpt35, priority=50)
])

# 3. 配置内存和回调
memory = PersistentMemory(session_id="prod_session")
obs = ObservabilityCallback()
metrics = MetricsAggregator()

# 4. 配置弹性组件
retry = RetryPolicy(max_retries=3)
breaker = CircuitBreaker(failure_threshold=5)

# 5. 创建Agent
my_agent = Agent(
    llm=pool_llm,
    tools=[search()],
    memory=memory,
    callbacks=[obs, metrics],
    system_instructions="你是一个专业助手。"
)

# 6. 使用弹性执行
async def robust_run(prompt: str):
    return await retry.execute_with_retry(
        breaker.call,
        my_agent.run,
        prompt
    )

# 7. 执行
result = await robust_run("你好")

# 8. 查看指标和健康状态
print(metrics.get_summary())
print(pool_llm.get_health_summary())
```

---

## 更多资源

- [用户指南](USER_GUIDE.md) - 详细使用教程
- [功能总览](V4_FINAL_SUMMARY.md) - v0.1.1所有特性
- [示例代码](examples/) - 更多示例

---

**Loom Agent v0.1.1 API Reference**
