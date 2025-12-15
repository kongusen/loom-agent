# Loom Agent 架构设计

**版本**: v0.1.6
**最后更新**: 2025-12-14

本文档介绍 Loom Agent v0.1.6 的核心架构和设计理念。

---

## 目录

1. [核心理念](#核心理念)
2. [架构概览](#架构概览)
3. [核心组件](#核心组件)
4. [执行流程](#执行流程)
5. [v0.1.6 特性](#v016-特性)
6. [设计原则](#设计原则)

---

## 核心理念

### Agent = 递归函数

Loom 的核心理念极其简洁：

```python
Agent = recursive function: Message → Message
```

**Agent 就是一个递归函数**，通过 `run(Message) -> Message` 的递归调用实现复杂行为。

### 为什么是递归？

传统框架使用复杂的状态机、图结构或循环：

```python
# ❌ 传统方式：复杂的状态管理
while not done:
    state = update_state(state)
    if需要工具:
        result = call_tool()
        state = update_state_with_result(result, state)
    ...
```

**Loom 的方式**：纯递归，简洁优雅：

```python
# ✅ Loom 方式：纯递归
async def run(message: Message) -> Message:
    # 1. LLM 推理
    response = await llm.generate(message)

    # 2. 如果需要工具
    if response.tool_calls:
        tool_results = await execute_tools(response.tool_calls)
        # 3. 递归！
        return await run(create_message_with_tool_results(tool_results))

    # 4. 返回最终结果
    return response
```

### Message - 统一载体

所有状态都封装在 **Message** 中：

```python
@dataclass
class Message:
    role: str              # "user" | "assistant" | "tool"
    content: str           # 文本内容
    tool_calls: List[...]  # 工具调用请求
    tool_results: List[...] # 工具执行结果
    metadata: dict         # 元数据
```

**Message 携带一切**：
- 对话历史通过 Message 链传递
- 工具调用请求在 Message 中
- 工具结果也在 Message 中
- 无需额外的状态管理

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      User Application                         │
└──────────────────────┬────────────────────────────────────────┘
                       │ Message
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      SimpleAgent                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              AgentExecutor                           │   │
│  │  • 递归状态机                                         │   │
│  │  • LLM 调用                                          │   │
│  │  • 工具编排                                          │   │
│  │  • 事件发射                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           ContextManager                             │   │
│  │  • 对话历史管理                                       │   │
│  │  • 上下文组装                                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            SkillManager (v0.1.6)                     │   │
│  │  • Skills 加载                                        │   │
│  │  • 渐进式披露                                         │   │
│  └─────────────────────────────────────────────────────┘   │
└───────┬──────────┬──────────┬──────────┬──────────┬─────────┘
        │          │          │          │          │
    ┌───▼──┐   ┌──▼───┐  ┌──▼────┐  ┌──▼─────┐ ┌─▼──────┐
    │ LLM  │   │Tools │  │Events │  │Skills  │ │Memory  │
    │      │   │      │  │       │  │        │ │        │
    └──────┘   └──────┘  └───────┘  └────────┘ └────────┘
```

---

## 核心组件

### 1. BaseAgent（协议）

定义 Agent 的基本接口：

```python
class BaseAgent(Protocol):
    """Agent 协议 - 递归状态机"""

    name: str
    llm: BaseLLM
    tools: List[BaseTool]

    async def run(self, message: Message) -> Message:
        """核心递归方法"""
        ...
```

**核心方法**：
- `run(Message) -> Message` - 唯一核心方法

### 2. SimpleAgent（实现）

最常用的 Agent 实现：

```python
class SimpleAgent:
    """基础递归 Agent"""

    def __init__(
        self,
        name: str,
        llm: BaseLLM,
        tools: List[BaseTool] = None,
        system_prompt: str = None,
        enable_skills: bool = True,
        max_recursion_depth: int = 20,
        ...
    ):
        self.executor = AgentExecutor(...)
        self.skill_manager = SkillManager(...)

    async def run(self, message: Message) -> Message:
        """委托给 AgentExecutor"""
        return await self.executor.execute(message)
```

**职责**：
- 配置和组装组件
- 委托执行给 AgentExecutor
- 管理 Skills 系统

### 3. AgentExecutor（执行引擎）

核心执行逻辑：

```python
class AgentExecutor:
    """Agent 执行引擎 - 递归状态机"""

    async def execute(self, message: Message) -> Message:
        """核心递归执行"""
        # 1. 发射 agent_start 事件
        self._emit_event(AgentEventType.AGENT_START, ...)

        # 2. 组装上下文
        context = self.context_manager.assemble(message)

        # 3. 调用 LLM
        self._emit_event(AgentEventType.LLM_START, ...)
        response = await self.llm.generate(context)
        self._emit_event(AgentEventType.LLM_END, ...)

        # 4. 如果有工具调用
        if response.tool_calls:
            # 并行执行工具 (v0.1.6)
            tool_results = await self._execute_tools(response.tool_calls)

            # 递归！
            return await self.execute(
                create_message_with_tool_results(tool_results)
            )

        # 5. 返回最终结果
        self._emit_event(AgentEventType.AGENT_END, ...)
        return response
```

**职责**：
- 递归状态机实现
- LLM 调用
- 工具编排和执行
- 事件发射
- 统计收集

**v0.1.6 增强**：
- ✅ 工具并行执行（3x 性能提升）
- ✅ 完整事件系统
- ✅ Token 统计

### 4. ContextManager（上下文管理）

管理对话历史和上下文：

```python
class ContextManager:
    """上下文管理器"""

    def __init__(self, max_context_tokens: int = 16000):
        self.messages: List[Message] = []
        self.max_context_tokens = max_context_tokens

    def add(self, message: Message):
        """添加消息到历史"""
        self.messages.append(message)

    def assemble(self, new_message: Message) -> List[Message]:
        """组装上下文"""
        # 1. 添加新消息
        self.add(new_message)

        # 2. 如果超过限制，压缩旧消息
        if self._estimate_tokens() > self.max_context_tokens:
            self._compress_old_messages()

        # 3. 返回完整上下文
        return [system_message] + self.messages
```

**职责**：
- 存储对话历史
- 上下文组装
- 自动压缩（超限时）

### 5. Message（统一消息）

Loom 的核心数据结构：

```python
@dataclass
class Message:
    """统一消息格式"""
    role: str                          # "user" | "assistant" | "tool"
    content: str                       # 文本内容
    tool_calls: Optional[List[...]]    # 工具调用
    tool_results: Optional[List[...]]  # 工具结果
    metadata: Dict[str, Any]           # 元数据
    timestamp: float                   # 时间戳
```

**设计理念**：
- 所有状态都在 Message 中
- 无需外部状态管理
- 简单、清晰、可追溯

### 6. SkillManager（Skills 系统）

v0.1.6 新增的模块化能力系统：

```python
class SkillManager:
    """Skills 管理器"""

    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}

    def load_all(self):
        """加载所有 Skills"""
        for skill_dir in self.skills_dir:
            skill = Skill.from_directory(skill_dir)
            self.skills[skill.name] = skill

    def get_system_prompt_section(self) -> str:
        """生成 Skills 索引（Layer 1）"""
        return "\n".join([
            skill.to_system_prompt_entry()
            for skill in self.skills.values()
            if skill.enabled
        ])
```

**三层渐进式披露**：
- Layer 1 (~50 tokens): 系统提示中的 Skills 索引
- Layer 2 (~500-2K tokens): 详细文档 (SKILL.md)
- Layer 3 (无限): 资源文件 (resources/)

### 7. Crew（多 Agent 协作）

多 Agent 协作框架：

```python
class Crew(BaseAgent):
    """多 Agent 协作系统"""

    def __init__(
        self,
        agents: List[BaseAgent],
        mode: str = "sequential",  # sequential | parallel | coordinated
        coordinator: BaseAgent = None,
        # v0.1.6 新特性
        use_smart_coordinator: bool = False,
        enable_parallel: bool = False,
        artifact_store: ArtifactStore = None,
        enable_error_recovery: bool = False,
        ...
    ):
        self.agents = agents
        self.mode = mode
        ...

    async def run(self, message: Message) -> Message:
        """根据模式执行"""
        if self.mode == "sequential":
            return await self._run_sequential(message)
        elif self.mode == "parallel":
            return await self._run_parallel(message)
        elif self.mode == "coordinated":
            return await self._run_coordinated(message)
```

**三种模式**：
- Sequential: 顺序流水线
- Parallel: 并行执行 + 聚合
- Coordinated: 智能协调分配

---

## 执行流程

### 单次执行流程

```
1. 用户输入 → Message(role="user", content="...")

2. Agent.run(message)
   ↓
3. AgentExecutor.execute(message)
   ├─ event: agent_start
   ├─ ContextManager.assemble() → 完整上下文
   ├─ event: llm_start
   ├─ LLM.generate() → Response
   ├─ event: llm_end
   └─ 判断是否有工具调用？
      ├─ 是 →
      │   ├─ event: tool_start (每个工具)
      │   ├─ 并行执行工具 (v0.1.6)
      │   ├─ event: tool_end (每个工具)
      │   └─ 递归调用 execute() ←─┐
      │                          │
      └─ 否 →                     │
          ├─ event: agent_end    │
          └─ 返回最终 Message ────┘

4. 返回给用户
```

### 递归工具调用示例

**用户**: "搜索并总结 AI Agent 的最新进展"

```
Iteration 1:
  LLM: 需要搜索 → tool_call("search", "AI Agent 2025")
  → 递归调用 run()

Iteration 2:
  LLM: 收到搜索结果，需要总结 → tool_call("summarize", results)
  → 递归调用 run()

Iteration 3:
  LLM: 有了总结，可以回答了 → 返回最终答案
  ✓ 递归结束
```

**关键**：每次递归都是完整的 `run(Message) -> Message`，没有外部状态。

---

## v0.1.6 特性

### 1. 工具并行执行

**旧版**（串行）：
```
tool1() → tool2() → tool3()  // 9 seconds
```

**v0.1.6**（并行）：
```
tool1() ┐
tool2() ├→ 并行执行  // 3 seconds
tool3() ┘
```

**性能提升**: **3x**

**实现**：
```python
async def _execute_tools(self, tool_calls):
    """并行执行工具"""
    tasks = [self._execute_single_tool(tc) for tc in tool_calls]
    results = await asyncio.gather(*tasks)
    return results
```

### 2. 完整事件系统

追踪 Agent 执行的全生命周期：

```python
# 事件类型
AgentEventType = {
    "AGENT_START",    # Agent 开始
    "AGENT_END",      # Agent 完成
    "AGENT_ERROR",    # Agent 错误
    "LLM_START",      # LLM 调用开始
    "LLM_END",        # LLM 调用完成
    "TOOL_START",     # 工具执行开始
    "TOOL_END",       # 工具执行完成
    "TOOL_ERROR",     # 工具执行错误
}

# 使用
def event_handler(event):
    print(f"[{event.type}] {event.data}")

agent.executor.event_handler = event_handler
```

### 3. Token 统计

完整的成本和性能分析：

```python
stats = agent.get_stats()
# {
#   "total_llm_calls": 5,
#   "total_tool_calls": 3,
#   "total_tokens_input": 1234,
#   "total_tokens_output": 567,
#   "total_errors": 0
# }

# 计算成本
cost = stats["total_tokens_input"] * 0.03/1000 + stats["total_tokens_output"] * 0.06/1000
```

### 4. Skills 系统

模块化能力扩展：

```
skills/
├── pdf_analyzer/
│   ├── skill.yaml          # Layer 1: 元数据
│   ├── SKILL.md            # Layer 2: 详细文档
│   └── resources/          # Layer 3: 资源文件
│       └── examples.json
├── web_research/
└── data_processor/
```

**渐进式披露**：
- Agent 只在系统提示中看到 Skills 索引（~50 tokens）
- 需要时才加载详细文档（~500-2K tokens）
- 资源文件按需访问（无限）

### 5. Crew 增强

多 Agent 协作的 6 大增强：

1. **SmartCoordinator**: 智能任务分解
2. **ParallelExecutor**: Agent 级并行
3. **ArtifactStore**: 大型结果管理
4. **ErrorRecovery**: 四层容错
5. **CheckpointManager**: 中断恢复
6. **CrewTracer**: 完整追踪

### 6. 工具启发式

自动生成的工具使用指南：

```python
# SimpleAgent 会自动生成：
system_prompt = """
You are assistant.

# Tool Usage Guidelines

1. Understand Available Tools
2. Match Tools to Intent
3. Prefer Specific Tools
4. Efficient Execution (parallel when possible)
5. Error Handling
6. Result Validation
"""
```

---

## 设计原则

### 1. 简单性

**核心理念极简**：
- Agent = 递归函数
- Message = 唯一状态载体
- 无复杂状态机

### 2. 可组合性

所有组件都是独立的：

```python
# 自由组合
agent = loom.agent(
    llm=OpenAILLM(...),           # 任何 LLM
    tools=[tool1, tool2],         # 任何工具
    context_manager=CustomContext(), # 自定义上下文
    enable_skills=True,           # 可选 Skills
)
```

### 3. 可扩展性

通过接口扩展：

```python
# 实现 BaseLLM 接口
class MyLLM(BaseLLM):
    async def generate(self, messages): ...

# 实现 BaseTool 接口
class MyTool(BaseTool):
    async def execute(self, **kwargs): ...

# 使用
agent = loom.agent(llm=MyLLM(), tools=[MyTool()])
```

### 4. 可观测性

完整的事件系统：
- 所有关键点都有事件
- 事件包含完整上下文
- 支持自定义处理器

### 5. 性能优先

- 工具并行执行（v0.1.6）
- Skills 渐进式披露
- 智能上下文压缩
- Crew 级并行

---

## 相关资源

- [SimpleAgent 指南](../guides/agents/simple-agent.md)
- [Crew 协作](../guides/patterns/crew.md)
- [Skills 系统](../guides/skills/overview.md)
- [API 参考](../api/)

---

## 下一步

- 阅读 [快速开始](../getting-started/quickstart.md)
- 学习 [创建第一个 Agent](../getting-started/first-agent.md)
- 查看 [API 参考](../api/agents.md)

---

**理解架构，构建更好的 Agent！** 🏗️
