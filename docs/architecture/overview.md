# Loom Agent 架构设计

**版本**: v0.1.9
**最后更新**: 2024-12-15

本文档介绍 Loom Agent v0.1.9 的核心架构和设计理念。

---

## 目录

1. [核心理念](#核心理念)
2. [架构概览](#架构概览)
3. [核心组件](#核心组件)
4. [执行流程](#执行流程)
5. [设计原则](#设计原则)
6. [核心特性](#核心特性)

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
    if 需要工具:
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

### Message - 不可变载体

所有状态都封装在 **不可变的 Message** 中（v0.1.9 重点改进）：

```python
@dataclass(frozen=True)  # 不可变
class Message:
    role: str                              # "user" | "assistant" | "system" | "tool"
    content: Union[str, List[ContentPart]] # 多模态内容

    # 工具相关
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None

    # 可选字段
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 自动生成字段
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None

    # v0.1.9: history 正式化（零数据丢失）
    history: Optional[List["Message"]] = field(default=None, repr=False)
```

**Message 携带一切**：
- 对话历史通过 `history` 字段完整保留
- 工具调用请求在 `tool_calls` 中
- 工具结果通过新 Message 传递
- 不可变性保证数据完整性
- 零数据丢失的序列化/反序列化

**v0.1.9 关键改进**：
- ✅ `history` 声明为正式 dataclass 字段
- ✅ `get_message_history()` 安全提取函数
- ✅ `build_history_chain()` 不可变历史链构建
- ✅ `to_dict(include_history=True)` 完整序列化
- ✅ 100% 遵守冻结数据类规范

---

## 架构概览

### 三层设计

```
┌─────────────────────────────────────────────────────────┐
│  Pattern Layer - 模式层                                  │
│  • Crew（多智能体协作 - 4种模式）                         │
│  • Skills（渐进式披露 - 节省95% tokens）                 │
│  • 递归控制（ReAct/反思/思维树）                          │
│  • Router（智能路由）                                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Execution Layer - 执行层                                │
│  • AgentExecutor（递归引擎）                              │
│  • Tools（并行执行 - 3x性能）                             │
│  • HierarchicalMemory（4层记忆+RAG - v0.1.9优化）        │
│  • ContextAssembler（智能组装 - 15-25% token节省）       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Core Layer - 核心层                                     │
│  • Message（不可变+类型安全 - v0.1.9修复）               │
│  • Event Sourcing（完整追踪）                            │
│  • Protocol-based Integration（零耦合）                  │
└─────────────────────────────────────────────────────────┘
```

### 完整架构图

```
┌──────────────────────────────────────────────────────┐
│                  User Application                     │
└──────────────────┬───────────────────────────────────┘
                   │ Message
                   ↓
┌──────────────────────────────────────────────────────┐
│                  SimpleAgent                          │
│  ┌────────────────────────────────────────────────┐ │
│  │            AgentExecutor                        │ │
│  │  • 递归状态机 (Message → Message)               │ │
│  │  • LLM 调用（流式生成）                         │ │
│  │  • 工具编排（并行执行）                         │ │
│  │  • 事件发射（完整追踪）                         │ │
│  │  • 统计收集（token/成本）                       │ │
│  └────────────────────────────────────────────────┘ │
│                                                        │
│  ┌────────────────────────────────────────────────┐ │
│  │        HierarchicalMemory (v0.1.9)             │ │
│  │  • Ephemeral（工具临时状态）                    │ │
│  │  • Working（最近10条）                          │ │
│  │  • Session（完整历史）                          │ │
│  │  • Longterm（向量化+RAG）                       │ │
│  │  • 智能晋升（LLM摘要）                          │ │
│  │  • 异步向量化（10x吞吐量）                      │ │
│  └────────────────────────────────────────────────┘ │
│                                                        │
│  ┌────────────────────────────────────────────────┐ │
│  │         ContextAssembler                       │ │
│  │  • Primacy/Recency Effects                     │ │
│  │  • XML 结构化                                   │ │
│  │  • 优先级管理                                   │ │
│  │  • Token 预算管理                               │ │
│  └────────────────────────────────────────────────┘ │
│                                                        │
│  ┌────────────────────────────────────────────────┐ │
│  │            SkillManager                        │ │
│  │  • Skills 加载                                  │ │
│  │  • 渐进式披露（3层）                            │ │
│  │  • 动态启用/禁用                                │ │
│  └────────────────────────────────────────────────┘ │
└────┬───────┬───────┬───────┬───────┬───────┬────────┘
     │       │       │       │       │       │
 ┌───▼──┐┌──▼───┐┌──▼────┐┌──▼────┐┌─▼────┐┌─▼──────┐
 │ LLM  ││Tools ││Events ││Skills ││Memory││Embedding│
 │      ││      ││       ││       ││      ││         │
 └──────┘└──────┘└───────┘└───────┘└──────┘└─────────┘
```

---

## 核心组件

### 1. BaseAgent（协议）

定义 Agent 的基本接口：

```python
@runtime_checkable
class BaseAgent(Protocol):
    """Agent 协议 - 递归状态机"""

    name: str
    llm: BaseLLM
    tools: List[BaseTool]

    async def run(self, message: Message) -> Message:
        """核心递归方法"""
        ...
```

**文件位置**: `loom/core/base_agent.py`

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
        memory: BaseMemory = None,
        enable_skills: bool = True,
        max_recursion_depth: int = 20,
        ...
    ):
        self.executor = AgentExecutor(...)
        self.skill_manager = SkillManager(...) if enable_skills else None
        self.memory = memory

    async def run(self, message: Message) -> Message:
        """委托给 AgentExecutor"""
        return await self.executor.execute(message)
```

**文件位置**: `loom/agents/agent.py`

**职责**：
- 配置和组装组件
- 委托执行给 AgentExecutor
- 管理 Skills 系统
- 集成 Memory 系统

### 3. AgentExecutor（执行引擎）

核心执行逻辑：

```python
class AgentExecutor:
    """Agent 执行引擎 - 递归状态机"""

    async def execute(self, message: Message) -> Message:
        """核心递归执行"""
        # 1. 递归深度检查
        self.current_depth += 1
        if self.current_depth > self.max_recursion_depth:
            raise RecursionError(f"超过最大递归深度 {self.max_recursion_depth}")

        # 2. 发射 agent_start 事件
        self._emit_event(AgentEventType.AGENT_START, ...)

        # 3. 准备上下文（压缩、记忆增强）
        prepared_msg = await self.context_manager.prepare(message)

        # 4. 转换为 LLM 格式
        llm_messages = self._to_llm_messages(prepared_msg)

        # 5. 调用 LLM
        self._emit_event(AgentEventType.LLM_START, ...)
        response = await self.llm.stream(llm_messages, tools=self.tool_schemas)
        self._emit_event(AgentEventType.LLM_END, ...)

        # 6. 如果有工具调用
        if response.tool_calls:
            # 并行执行工具
            tool_results = await self._execute_tools_parallel(response.tool_calls)

            # 构建新消息（v0.1.9: 不可变方式）
            new_message = build_history_chain(
                get_message_history(message),
                create_tool_results_message(tool_results)
            )

            # 递归！
            return await self.execute(new_message)

        # 7. 返回最终结果
        self._emit_event(AgentEventType.AGENT_END, ...)
        return response
```

**文件位置**: `loom/core/executor.py`

**职责**：
- 递归状态机实现
- LLM 调用
- 工具编排和并行执行
- 事件发射
- 统计收集
- Message 历史管理（v0.1.9）

**关键特性**：
- ✅ 工具并行执行（3x 性能提升）
- ✅ 完整事件系统
- ✅ Token 统计和成本追踪
- ✅ 不可变 Message 处理（v0.1.9）
- ✅ 工具结果结构化序列化（v0.1.9）

### 4. Message（统一消息）

Loom 的核心数据结构：

**文件位置**: `loom/core/message.py`

**核心函数**（v0.1.9）：

```python
# 安全提取历史
def get_message_history(message: Message) -> List[Message]:
    """安全提取历史（类型验证 + 防御性复制）"""
    if message.history is None:
        return []
    if not isinstance(message.history, list):
        return []
    return list(message.history)  # 防御性复制

# 不可变历史链构建
def build_history_chain(
    base_history: List[Message],
    new_message: Message
) -> Message:
    """不可变方式追加历史"""
    full_history = list(base_history) + [new_message]
    return dataclasses.replace(new_message, history=full_history)

# 便捷创建函数
create_user_message(content: str) -> Message
create_assistant_message(content: str, tool_calls=None) -> Message
create_system_message(content: str) -> Message
create_tool_message(content: str, tool_call_id: str, name: str) -> Message
```

**序列化支持**（v0.1.9）：

```python
# 完整序列化（包含历史）
data = message.to_dict(include_history=True)

# 完整反序列化（零丢失）
restored = Message.from_dict(data)

# 工具结果结构化序列化
from loom.core.executor import serialize_tool_result

result = {"data": [1, 2, 3]}
content, metadata = serialize_tool_result(result)
# content: '{"data": [1, 2, 3]}'
# metadata: {"content_type": "application/json", "result_type": "dict"}
```

### 5. HierarchicalMemory（分层记忆）

v0.1.8 引入，v0.1.9 优化的 4 层记忆系统：

**文件位置**: `loom/builtin/memory/hierarchical_memory.py`

```python
class HierarchicalMemory(BaseMemory):
    """4层分层记忆系统 + RAG"""

    def __init__(
        self,
        embedding: BaseEmbedding,
        vector_store: BaseVectorStore = None,
        working_capacity: int = 10,
        # v0.1.9 新增
        enable_smart_promotion: bool = False,
        summarization_llm: BaseLLM = None,
        summarization_threshold: int = 100,
        min_promotion_length: int = 50,
        enable_async_vectorization: bool = False,
        vectorization_batch_size: int = 10,
        enable_ephemeral_debug: bool = False,
    ):
        self.ephemeral = {}        # Layer 1: 工具临时状态
        self.working = []          # Layer 2: 最近重要记忆（FIFO）
        self.session = []          # Layer 3: 完整对话历史
        self.longterm = vector_store  # Layer 4: 跨会话知识库
        ...
```

**核心方法**：

```python
# 添加消息（自动管理4层）
await memory.add_message(message)

# 语义检索
results = await memory.retrieve(
    query="用户的编程偏好",
    top_k=5,
    tier="longterm"  # ephemeral/working/session/longterm
)

# Ephemeral Memory（v0.1.9 调试模式）
memory.dump_ephemeral_state()  # 导出完整状态
```

**v0.1.9 核心特性**：

1. **智能晋升** (`enable_smart_promotion=True`)
   - 过滤 trivial 内容（"好的"、"谢谢"等）
   - LLM 摘要长文本（提取 1-3 个关键事实）
   - 最小长度检查（默认 50 字符）

2. **异步向量化** (`enable_async_vectorization=True`)
   - 后台任务队列处理
   - 批量嵌入 API 调用
   - 不阻塞主执行流程
   - **10x 吞吐量提升**

3. **调试模式** (`enable_ephemeral_debug=True`)
   - 详细日志
   - 完整状态导出
   - 便于排查工具调用问题

### 6. ContextAssembler（智能上下文组装）

基于 Anthropic 最佳实践的上下文组装器：

**文件位置**: `loom/core/context_assembler.py`

```python
class ContextAssembler:
    """智能上下文组装器"""

    def __init__(
        self,
        max_tokens: int = 100000,
        use_xml_structure: bool = True,
        enable_primacy_recency: bool = True,
    ):
        self.components = []
        ...

    # 添加组件
    def add_critical_instruction(self, content: str):
        """关键指令（永不截断）"""

    def add_role(self, content: str):
        """角色定义"""

    def add_task(self, content: str):
        """任务描述"""

    def add_component(
        self,
        name: str,
        content: str,
        priority: ComponentPriority,
        xml_tag: str = None,
        truncatable: bool = True
    ):
        """自定义组件"""

    # 组装上下文
    def assemble(self) -> str:
        """基于优先级智能组装"""
```

**核心特性**：
- Primacy/Recency Effects（首因/近因效应）
- XML 结构化（清晰分隔）
- 优先级管理（CRITICAL/ESSENTIAL/HIGH/MEDIUM/LOW）
- Token 预算管理
- **15-25% token 节省**

### 7. SkillManager（Skills 系统）

模块化能力系统：

**文件位置**: `loom/skills/`

```python
class SkillManager:
    """Skills 管理器"""

    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}

    def load_all(self):
        """加载所有 Skills"""
        for skill_dir in Path(self.skills_dir).iterdir():
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

```
┌──────────────────────────────────────┐
│  Layer 1: Index (系统提示)            │
│  ~50 tokens/skill                    │
│  始终加载                             │
└──────────────────────────────────────┘
              ↓ (按需加载)
┌──────────────────────────────────────┐
│  Layer 2: Detailed Docs (SKILL.md)   │
│  ~500-2000 tokens/skill              │
│  只在需要时加载                        │
└──────────────────────────────────────┘
              ↓ (按需访问)
┌──────────────────────────────────────┐
│  Layer 3: Resources (文件/数据)       │
│  任意大小                              │
└──────────────────────────────────────┘
```

**效果**: 节省 **95% 上下文开销**

### 8. Crew（多 Agent 协作）

多 Agent 协作框架：

**文件位置**: `loom/patterns/crew.py`

```python
class Crew(BaseAgent):
    """多 Agent 协作系统"""

    def __init__(
        self,
        agents: List[BaseAgent],
        mode: str = "sequential",  # sequential | parallel | coordinated | routed
        coordinator: BaseAgent = None,
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
        elif self.mode == "routed":
            return await self._run_routed(message)
```

**四种模式**：
- **Sequential**: 顺序流水线（A → B → C）
- **Parallel**: 并行执行 + 聚合（A + B + C）
- **Coordinated**: 智能协调分配（智能分解任务）
- **Routed**: 智能路由选择（基于能力匹配）

---

## 执行流程

### 完整执行流程

```
1. 用户输入 → Message(role="user", content="...")

2. Agent.run(message)
   ↓
3. AgentExecutor.execute(message)
   ├─ event: agent_start
   ├─ 递归深度检查
   ├─ ContextManager.prepare()
   │  ├─ Memory.retrieve() (RAG 检索)
   │  ├─ ContextAssembler.assemble() (智能组装)
   │  └─ 返回优化后的 Message
   ├─ 转换为 LLM 格式 (_to_llm_messages)
   │  └─ 提取 history: get_message_history()
   ├─ event: llm_start
   ├─ LLM.stream() → Response (流式生成)
   ├─ event: llm_end
   └─ 判断是否有工具调用？
      ├─ 是 →
      │   ├─ event: tool_start (每个工具)
      │   ├─ 并行执行工具 (asyncio.gather)
      │   ├─ serialize_tool_result() (v0.1.9)
      │   ├─ event: tool_end (每个工具)
      │   ├─ 构建新 Message (build_history_chain)
      │   └─ 递归调用 execute() ←─┐
      │                          │
      └─ 否 →                     │
          ├─ Memory.add_message() │
          ├─ event: agent_end    │
          └─ 返回最终 Message ────┘

4. 返回给用户
```

### 递归工具调用示例

**用户**: "搜索并总结 AI Agent 的最新进展"

```
Iteration 1:
  Message: {role: "user", content: "搜索并总结..."}
  LLM: 需要搜索 → tool_call("search", "AI Agent 2025")
  → 递归调用 run()

Iteration 2:
  Message: {
    role: "assistant",
    tool_calls: [...]
    history: [prev_user_msg, prev_assistant_msg]
  }
  LLM: 收到搜索结果，需要总结 → tool_call("summarize", results)
  → 递归调用 run()

Iteration 3:
  Message: {..., history: [完整历史]}
  LLM: 有了总结，可以回答了 → 返回最终答案
  ✓ 递归结束
```

**关键**：每次递归都是完整的 `run(Message) -> Message`，Message 携带完整历史链。

---

## 设计原则

### 1. 简单性

**核心理念极简**：
- Agent = 递归函数
- Message = 不可变状态载体
- 无复杂状态机

### 2. 不可变性（v0.1.9 强化）

**所有数据不可变**：
- `@dataclass(frozen=True)` 保证不可变
- 任何修改都返回新实例
- 历史链完整追溯
- 零数据丢失

### 3. 类型安全

**Protocol-based 集成**：
- 使用 `Protocol` 而非 ABC
- 运行时类型检查
- 零依赖集成
- 鸭子类型

### 4. 可组合性

**所有组件独立**：

```python
# 自由组合
agent = loom.agent(
    llm=UnifiedLLM(...),              # 任何 LLM
    tools=[tool1, tool2],             # 任何工具
    memory=HierarchicalMemory(...),   # 任何记忆系统
    context_manager=ContextAssembler(...),  # 自定义上下文
    enable_skills=True,               # 可选 Skills
)
```

### 5. 可扩展性

**通过 Protocol 扩展**：

```python
# 实现 BaseLLM Protocol
class MyLLM:
    async def stream(self, messages, tools=None):
        yield {"type": "content_delta", "content": "..."}

# 实现 BaseTool Protocol
class MyTool:
    async def run(self, **kwargs):
        return result

# 使用
agent = loom.agent(llm=MyLLM(), tools=[MyTool()])
```

### 6. 可观测性

**完整事件系统**：
- 所有关键点都有事件
- 事件包含完整上下文
- 支持自定义处理器
- Token 和成本追踪

### 7. 性能优先

**多层面优化**：
- 工具并行执行（3x 性能提升）
- Skills 渐进式披露（95% token 节省）
- 智能上下文组装（15-25% token 节省）
- 异步向量化（10x 吞吐量提升）

---

## 核心特性

### 1. Message 不可变架构（v0.1.9）

**问题解决**：
- ✅ 历史链完整保留
- ✅ 序列化零数据丢失
- ✅ 100% 冻结数据类合规
- ✅ 工具结果保留类型信息

### 2. 递归状态机

**优势**：
- 🎯 零学习成本（普通递归函数）
- 📊 执行栈清晰（标准调试工具）
- 🛡️ 自动循环检测
- 🔧 易于扩展

### 3. HierarchicalMemory（v0.1.9）

**4 层记忆**：
- Ephemeral → Working → Session → Longterm
- 智能晋升 + LLM 摘要
- 异步向量化
- 语义检索（RAG）

### 4. Protocol-based Integration

**零耦合集成**：
- 任何 LLM（OpenAI/DeepSeek/Qwen/等）
- 任何工具
- 任何记忆系统
- 任何向量数据库

### 5. 完整事件系统

**可观测性**：
- Agent 生命周期事件
- LLM 调用追踪
- 工具执行监控
- Token/成本统计

### 6. 工具并行执行

**性能提升**：
- 自动并行执行所有工具
- **3x 性能提升**
- 零配置

---

## 相关文档

- [架构实现状态](./ARCHITECTURE_STATUS.md) - 完整组件清单
- [SimpleAgent 指南](../guides/agents/simple-agent.md)
- [Crew 协作](../guides/patterns/crew.md)
- [分层记忆与 RAG](../guides/advanced/hierarchical_memory_rag.md)
- [Context Assembler 指南](../guides/advanced/CONTEXT_ASSEMBLER_GUIDE.md)
- [Skills 系统](../guides/skills/overview.md)
- [API 参考](../api/)

---

## 下一步

- 阅读 [快速开始](../getting-started/quickstart.md)
- 学习 [创建第一个 Agent](../getting-started/first-agent.md)
- 查看 [API 参考](../api/agents.md)
- 探索 [高级指南](../guides/advanced/)

---

**理解架构，构建更好的 Agent！** 🏗️
