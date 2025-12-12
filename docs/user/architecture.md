# Loom Agent v0.1.1 架构文档

**系统架构** | **组件关系** | **执行流程**

---

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        User Application                       │
│                    (Your Python Code)                         │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ agent.execute(input)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                         Agent Layer                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           AgentExecutor (Core Engine)                 │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │   tt() Recursive Control Loop                  │  │  │
│  │  │   ├─ Frame Management                          │  │  │
│  │  │   ├─ Context Assembly                          │  │  │
│  │  │   ├─ LLM Streaming                             │  │  │
│  │  │   ├─ Tool Execution                            │  │  │
│  │  │   └─ Recursive Calls                           │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└──────┬───────┬────────┬─────────┬──────────┬──────────┬────┘
       │       │        │         │          │          │
   ┌───▼───┐ ┌▼──────┐ ┌▼───────┐ ┌▼────────┐ ┌▼────────┐ ┌▼─────┐
   │  LLM  │ │ Tools │ │ Memory │ │ Context │ │ Compress│ │Hooks │
   │       │ │       │ │        │ │Assembly │ │         │ │      │
   └───┬───┘ └┬──────┘ └┬───────┘ └┬────────┘ └┬────────┘ └┬─────┘
       │      │         │          │           │           │
       └──────┴─────────┴──────────┴───────────┴───────────┘
                              │
                     AgentEvent Stream
                              │
                              ↓
                  ┌───────────────────────┐
                  │   EventJournal        │
                  │   (Persistence)       │
                  └───────────────────────┘
```

---

## 🔄 执行流程（tt递归循环）

```
User Input
    │
    ↓
┌───────────────────────────────────────────────────────────┐
│ tt(messages, turn_state, context) - Iteration N           │
│                                                             │
│  Step 1: Lifecycle Hook - before_iteration_start          │
│      ↓                                                      │
│  Step 2: Context Assembly                                  │
│      ├─ Emit CONTEXT_ASSEMBLY_START                       │
│      ├─ Gather components (system, history, tools, RAG)   │
│      ├─ Check token budget                                │
│      ├─ Apply priorities                                   │
│      ├─ Truncate/exclude low-priority components          │
│      ├─ Emit COMPONENT_INCLUDED/TRUNCATED/EXCLUDED        │
│      └─ Emit CONTEXT_ASSEMBLY_COMPLETE                    │
│      ↓                                                      │
│  Step 3: Check Compression Needed?                        │
│      ├─ If tokens >= 92% threshold:                       │
│      │   ├─ Emit COMPRESSION_START                        │
│      │   ├─ Call LLM for 8-segment summary               │
│      │   ├─ Retry with backoff (3 attempts)              │
│      │   ├─ Emit COMPRESSION_PROGRESS (retries)          │
│      │   ├─ On failure: Emit COMPRESSION_FALLBACK        │
│      │   │   └─ Use sliding window                       │
│      │   └─ Emit COMPRESSION_COMPLETE                    │
│      └─ Else: Skip compression                            │
│      ↓                                                      │
│  Step 4: LLM Call (Streaming)                             │
│      ├─ Lifecycle Hook: before_llm_call                   │
│      ├─ Emit LLM_START                                    │
│      ├─ Stream response chunks                            │
│      ├─ Emit LLM_DELTA (for each chunk)                  │
│      ├─ Parse tool calls (if any)                        │
│      ├─ Emit LLM_COMPLETE                                │
│      └─ Lifecycle Hook: after_llm_response               │
│      ↓                                                      │
│  Step 5: Tool Calls Detected?                             │
│      ├─ YES: Execute Tools                                │
│      │   ├─ For each tool call:                          │
│      │   │   ├─ Lifecycle Hook: before_tool_execution   │
│      │   │   ├─ Check permissions (HITL)                │
│      │   │   ├─ Emit TOOL_EXECUTION_START               │
│      │   │   ├─ Execute tool                            │
│      │   │   ├─ Emit TOOL_RESULT or TOOL_ERROR          │
│      │   │   └─ Lifecycle Hook: after_tool_execution    │
│      │   ├─ Add tool results to messages                │
│      │   └─ Emit RECURSION                              │
│      │       ↓                                            │
│      │   ┌─────────────────────────────┐                │
│      │   │ tt(messages, turn_state+1)   │ ← Recurse     │
│      │   └─────────────────────────────┘                │
│      │                                                    │
│      └─ NO: Final Response                               │
│          ├─ Emit AGENT_FINISH                            │
│          └─ Return result                                │
│                                                            │
│  Step 6: Check Termination                                │
│      ├─ Max iterations reached? → Emit ERROR             │
│      ├─ Cancel token set? → Emit ERROR                   │
│      └─ Final response? → DONE                           │
│                                                            │
└───────────────────────────────────────────────────────────┘
    │
    ↓
Final Result → User
```

---

## 📦 核心组件详解

### 1. AgentExecutor（执行引擎）

**职责**：
- 管理递归执行循环（tt函数）
- 协调所有子组件
- 处理事件流

**关键方法**：
```python
async def tt(
    messages: List[Message],
    turn_state: TurnState,
    context: ExecutionContext
) -> AsyncGenerator[AgentEvent, None]:
    """
    Tail-recursive control loop
    - 组装上下文
    - 调用LLM
    - 执行工具
    - 递归调用自己
    """
```

**状态管理**：
- `TurnState`: 不可变状态（迭代次数、取消标志）
- `ExecutionContext`: 执行上下文（工作目录、关联ID）
- `ExecutionFrame`: 执行帧（历史、上下文fabric）

---

### 2. LLM Layer（大语言模型层）

**设计**：Protocol-based（v0.1.1）

```python
@runtime_checkable
class BaseLLM(Protocol):
    """LLM接口 - 零耦合设计"""
    
    async def stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamEvent, None]:
        """流式生成 - 所有LLM调用的唯一入口"""
        ...
```

**支持的Provider**：
- OpenAI (gpt-4, gpt-3.5-turbo)
- Anthropic (claude-3-opus, claude-3-sonnet)
- Azure OpenAI
- 自定义LLM（实现Protocol即可）

**流式架构优势**：
- 实时响应（用户体验好）
- Token-by-token控制
- 早期终止支持
- 统一接口

---

### 3. Tools System（工具系统）

**架构**：

```
┌──────────────────────────────────────┐
│         ToolPipeline                  │
│  ┌────────────────────────────────┐  │
│  │  1. Permission Check           │  │
│  │     (PermissionManager)        │  │
│  └────────────────────────────────┘  │
│              ↓                        │
│  ┌────────────────────────────────┐  │
│  │  2. Lifecycle Hook             │  │
│  │     (before_tool_execution)    │  │
│  └────────────────────────────────┘  │
│              ↓                        │
│  ┌────────────────────────────────┐  │
│  │  3. Tool Execution             │  │
│  │     (BaseTool.execute())       │  │
│  └────────────────────────────────┘  │
│              ↓                        │
│  ┌────────────────────────────────┐  │
│  │  4. Result Processing          │  │
│  │     (ToolResult)               │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

**内置工具**：
- ReadFileTool
- WriteFileTool
- EditFileTool
- GlobTool
- GrepTool
- BashTool
- WebSearchTool

**工具接口**：
```python
class BaseTool:
    name: str
    description: str
    parameters: Dict
    
    async def execute(self, **kwargs) -> str:
        """执行工具"""
```

---

### 4. Memory System（内存系统 - v0.1.1 Stream-First）

**三层架构**：

```
┌─────────────────────────────────────┐
│  Tier 1: Short-term Memory          │
│  (In-memory message array)           │
│  - 当前会话                          │
│  - 快速访问                          │
└───────────┬─────────────────────────┘
            │
┌───────────▼─────────────────────────┐
│  Tier 2: Mid-term Memory             │
│  (Compression summaries)             │
│  - 8-segment structured summary      │
│  - 70-80% token reduction            │
└───────────┬─────────────────────────┘
            │
┌───────────▼─────────────────────────┐
│  Tier 3: Long-term Memory            │
│  (JSON file persistence)             │
│  - 跨会话持久化                      │
│  - 自动备份                          │
└─────────────────────────────────────┘
```

**Stream-First API**：
```python
# 核心流式方法
async def add_message_stream(msg) -> AsyncGenerator[AgentEvent]:
    yield MEMORY_ADD_START
    # Add to storage
    if persistence_enabled:
        yield MEMORY_SAVE_START
        save_to_disk()
        yield MEMORY_SAVE_COMPLETE
    yield MEMORY_ADD_COMPLETE

# 便捷包装器
async def add_message(msg):
    async for event in add_message_stream(msg):
        pass  # Consume stream
```

---

### 5. Context Assembly（上下文组装 - v0.1.1 Stream-First）

**优先级系统**：

```
Priority Levels:
┌─────────────────────────────────────┐
│ CRITICAL (100)                       │ ← System instructions (Never removed)
├─────────────────────────────────────┤
│ HIGH (90)                            │ ← RAG documents, Important config
├─────────────────────────────────────┤
│ MEDIUM (70)                          │ ← Tool definitions, Examples
├─────────────────────────────────────┤
│ LOW (50)                             │ ← Conversation history
├─────────────────────────────────────┤
│ OPTIONAL (30)                        │ ← Scratch pad, Temp notes
└─────────────────────────────────────┘
```

**Token Budget管理**：

```
组件添加流程：
1. 排序组件（按优先级降序）
2. 添加non-truncatable组件
   ├─ 如果超出budget → EXCLUDED
   └─ 如果适合 → INCLUDED
3. 添加truncatable组件
   ├─ 如果完整适合 → INCLUDED
   ├─ 如果部分适合 → TRUNCATED
   └─ 如果不适合 → EXCLUDED
4. Emit ASSEMBLY_COMPLETE
```

**Stream-First监控**：
```python
async for event in assembler.assemble_stream():
    if event.type == CONTEXT_COMPONENT_TRUNCATED:
        log(f"Truncated: {event.metadata['component_name']}")
```

---

### 6. Compression Manager（压缩管理器 - v0.1.1 Stream-First）

**8-Segment Compression**：

```
原始消息（45条，8000 tokens）
    ↓
LLM压缩（GPT-4）
    ↓
8段结构化摘要（2000 tokens）
    ├─ Task Overview
    ├─ Key Decisions
    ├─ Progress
    ├─ Blockers
    ├─ Open Items
    ├─ Context
    ├─ Next Steps
    └─ Metadata
```

**重试机制**：

```
Attempt 1 → LLM Call
    ├─ Success → Return summary
    └─ Failure → Backoff 1s
Attempt 2 → LLM Call
    ├─ Success → Return summary
    └─ Failure → Backoff 2s
Attempt 3 → LLM Call
    ├─ Success → Return summary
    └─ Failure → Backoff 4s
Max Retries Reached
    ↓
Fallback: Sliding Window
    └─ Keep last N messages
```

**Stream-First Observability**：
```python
async for event in compressor.compress_stream(messages):
    if event.type == COMPRESSION_PROGRESS:
        if event.metadata['status'] == 'retry':
            print(f"Retry {event.metadata['attempt']}")
    elif event.type == COMPRESSION_FALLBACK:
        print(f"Fallback: {event.metadata['fallback_method']}")
```

---

### 7. Lifecycle Hooks（生命周期钩子）

**Hook Points（按执行顺序）**：

```
Iteration N Start
    ↓
[1] before_iteration_start
    ↓
[2] before_context_assembly
    ↓
Context Assembly
    ↓
[3] after_context_assembly
    ↓
[4] before_llm_call
    ↓
LLM Streaming
    ↓
[5] after_llm_response
    ↓
Tool Calls?
    ├─ YES:
    │   ↓
    │  [6] before_tool_execution ← HITL拦截点
    │   ↓
    │  Tool Execution
    │   ↓
    │  [7] after_tool_execution
    │   ↓
    │  [8] before_recursion
    │   ↓
    │  Recurse to tt()
    │
    └─ NO:
        ↓
       [9] after_iteration_end
        ↓
       Return
```

**内置Hooks**：
- `HITLHook`: 人在回路中（危险工具拦截）
- `LoggingHook`: 执行日志
- `MetricsHook`: 性能指标收集

---

### 8. Crew System（多Agent协作）

**架构**：

```
┌─────────────────────────────────────────┐
│            Crew (Coordinator)            │
│  ┌───────────────────────────────────┐  │
│  │    OrchestrationPlan              │  │
│  │    ├─ Mode: SEQUENTIAL/PARALLEL   │  │
│  │    ├─ Tasks: [t1, t2, t3]        │  │
│  │    └─ Dependencies: Graph         │  │
│  └───────────────────────────────────┘  │
│                  │                       │
│     ┌────────────┼────────────┐         │
│     │            │            │         │
│  ┌──▼──┐     ┌──▼──┐     ┌──▼──┐      │
│  │Agent│     │Agent│     │Agent│      │
│  │  1  │     │  2  │     │  3  │      │
│  └──┬──┘     └──┬──┘     └──┬──┘      │
└─────┼──────────┼──────────┼───────────┘
      │          │          │
      └──────────┴──────────┘
              │
       SharedState / MessageBus
```

**执行模式**：

```
SEQUENTIAL:
    Task1 → Task2 → Task3

PARALLEL:
    Task1 ─┐
    Task2 ─┼→ (同时执行)
    Task3 ─┘

CONDITIONAL:
    Task1
      ↓
    if condition:
      Task2
    else:
      Task3

HIERARCHICAL:
    Manager
      ├→ Worker1
      ├→ Worker2
      └→ Worker3
```

---

## 🔄 数据流

### 消息流

```
User Input
    ↓
Message(role="user", content="...")
    ↓
Memory.add_message()
    ↓
Context Assembly
    ↓
LLM Input: [system, history, user, tools]
    ↓
LLM Output: text + tool_calls
    ↓
Tool Execution
    ↓
Message(role="tool", content=result)
    ↓
Memory.add_message()
    ↓
Recurse (tt loop)
    ↓
Final Response
    ↓
Message(role="assistant", content="...")
    ↓
User
```

### 事件流

```
Agent.execute(input)
    ↓
AsyncGenerator[AgentEvent]
    ├─ AGENT_START
    ├─ ITERATION_START (N=1)
    ├─ CONTEXT_ASSEMBLY_START
    ├─ CONTEXT_COMPONENT_INCLUDED
    ├─ CONTEXT_ASSEMBLY_COMPLETE
    ├─ LLM_START
    ├─ LLM_DELTA (×100)
    ├─ LLM_TOOL_CALLS
    ├─ LLM_COMPLETE
    ├─ TOOL_EXECUTION_START
    ├─ TOOL_RESULT
    ├─ RECURSION
    ├─ ITERATION_START (N=2)
    ├─ ... (重复)
    └─ AGENT_FINISH
    ↓
User consumes events
```

---

## 🎯 设计原则

### 1. Stream-First Architecture（v0.1.1核心）

**理念**：所有核心操作都是流式的

```python
# 核心方法返回 AsyncGenerator[AgentEvent]
async def operation_stream() -> AsyncGenerator[AgentEvent]:
    yield START_EVENT
    # ... work ...
    yield COMPLETE_EVENT

# 便捷包装器消费流
async def operation():
    async for event in operation_stream():
        pass  # Consume
    return result
```

**优势**：
- 实时进度可见
- 完整可观察性
- 事件可记录/重放
- 向后兼容

---

### 2. Protocol over ABC

**v0.1.0**:
```python
class BaseLLM(ABC):
    @abstractmethod
    def generate(self): ...
```

**v0.1.1**:
```python
@runtime_checkable
class BaseLLM(Protocol):
    async def stream(self): ...
```

**优势**：
- 零耦合
- Duck typing
- 无继承要求
- 更灵活

---

### 3. Immutable State

**TurnState**（不可变）:
```python
@dataclass(frozen=True)
class TurnState:
    iteration: int
    max_iterations: int
    is_cancelled: bool
    
    def next_iteration(self) -> TurnState:
        return TurnState(
            iteration=self.iteration + 1,
            max_iterations=self.max_iterations,
            is_cancelled=self.is_cancelled
        )
```

**优势**：
- 无副作用
- 易于调试
- 并发安全
- 可预测

---

### 4. Event Sourcing

**所有操作产生事件**：

```python
Operation → [Event1, Event2, ...] → State
```

**优势**：
- 完整审计日志
- 时间旅行调试
- Crash recovery
- 可重放

---

## 📊 性能特性

### Token使用优化

```
不压缩:  8000 tokens/iteration
    ↓ 92% threshold
启用压缩: 2000 tokens/iteration (75% reduction)
    ↓ 8-segment summary
持续执行: 50+ iterations without overflow
```

### 并行执行（Crew）

```
Sequential:  3 tasks × 30s = 90s
    ↓
Parallel:    3 tasks → 30s (3x faster)
```

### 缓存策略

```
ContextAssembler:
- Component cache (LRU, max 100)
- Assembly cache (hash-based)
- 命中率: ~70%

Memory:
- 自动备份 (max 5 files)
- 增量保存
```

---

## 🔐 安全特性

### 1. HITL（Human-in-the-Loop）

```python
HITLHook(
    dangerous_tools=["bash", "write_file", "delete_file"],
    ask_handler=lambda msg: user_confirm(msg)
)
```

**拦截时机**: `before_tool_execution` hook

---

### 2. Permission System

```python
PermissionManager(
    policy={"bash": "deny", "read_file": "allow"},
    default="ask"
)
```

---

### 3. Sandbox Mode

```python
agent(
    llm=llm,
    tools=[ReadFileTool()],  # 仅只读工具
    safe_mode=True           # 所有工具需确认
)
```

---

## 📈 可扩展性

### 自定义LLM

```python
class MyLLM:
    async def stream(self, messages, tools=None, **kwargs):
        # 实现Protocol
        yield LLMStreamEvent(type="delta", content="...")
```

### 自定义Tool

```python
class MyTool(BaseTool):
    name = "my_tool"
    description = "..."
    
    async def execute(self, **kwargs) -> str:
        return "result"
```

### 自定义Hook

```python
class MyHook(LifecycleHook):
    async def before_llm_call(self, frame, messages):
        log(f"LLM call with {len(messages)} messages")
        return None
```

---

## 🎓 总结

**Loom Agent v0.1.1 核心特性**：

1. **Stream-First** - 100%架构一致性
2. **Event Sourcing** - 完整可观察性
3. **Recursive State Machine** - 优雅的控制流
4. **Protocol-based** - 零耦合设计
5. **Crash Recovery** - 生产就绪
6. **Multi-Agent** - Crew协作系统
7. **Human-in-the-Loop** - 安全保障
8. **Context Management** - 智能token管理

**适用场景**：
- 代码分析与生成
- 数据处理Pipeline
- 研究与报告生成
- 复杂工作流自动化
- 需要人工监督的任务
- 需要crash recovery的长任务

---

**Version**: v0.1.1  
**Last Updated**: 2024-12-12  
**License**: MIT
